import BackendStatus from "@/components/BackendStatus";
import GeocodeSearch from "@/components/GeocodeSearch";

export default function Home() {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Dashboard</h2>
      <BackendStatus />
      <GeocodeSearch />
    </div>
  );
}
