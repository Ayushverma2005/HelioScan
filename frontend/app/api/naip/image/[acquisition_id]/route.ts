import { getApiBaseUrl } from "@/lib/api";

const ACQUISITION_ID_PATTERN = /^naip_[0-9]{8}T[0-9]{6}\.[0-9]{6}Z$/;

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ acquisition_id: string }> },
): Promise<Response> {
  const { acquisition_id } = await params;
  if (!ACQUISITION_ID_PATTERN.test(acquisition_id)) {
    return Response.json(
      {
        detail: {
          code: "naip_image_not_found",
          message: "NAIP imagery could not be found.",
        },
      },
      { status: 404 },
    );
  }

  const baseUrl = getApiBaseUrl();

  try {
    const response = await fetch(`${baseUrl}/api/imagery/naip/${acquisition_id}/image`, {
      cache: "no-store",
      signal: AbortSignal.timeout(30000),
    });

    if (!response.ok) {
      return Response.json(
        {
          detail: {
            code: "naip_image_not_found",
            message: "NAIP imagery could not be found.",
          },
        },
        { status: response.status },
      );
    }

    const body = await response.arrayBuffer();
    const contentType = response.headers.get("content-type") ?? "image/tiff";
    const contentDisposition = response.headers.get("content-disposition");

    return new Response(body, {
      status: 200,
      headers: {
        "Cache-Control": "private, no-store",
        "Content-Type": contentType,
        ...(contentDisposition ? { "Content-Disposition": contentDisposition } : {}),
      },
    });
  } catch {
    return Response.json(
      {
        detail: {
          code: "naip_image_unavailable",
          message: "Unable to retrieve the acquired NAIP image.",
        },
      },
      { status: 502 },
    );
  }
}
