import { useState, useEffect } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Users, Building2, TrendingUp, MapPin, Home, Loader2, AlertCircle, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";
import client from "../api/client";

export default function AdminDashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Admin stats
  const [totalUsers, setTotalUsers] = useState(0);
  const [totalProperties, setTotalProperties] = useState(0);
  const [byCity, setByCity] = useState({});
  const [byType, setByType] = useState({});

  // Market summary
  const [marketSummary, setMarketSummary] = useState(null);

  // Users list
  const [users, setUsers] = useState([]);

  // All properties for status chart
  const [allProperties, setAllProperties] = useState([]);

  const STATUS_COLORS = {
    approved: "#16a34a",
    sold: "#dc2626",
    pending: "#ca8a04",
    rejected: "#ef4444",
    available: "#16a34a",
  };

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Admin stats (total users, total properties, by_city, by_type)
      const adminStatsRes = await client.get("/admin/stats");
      setTotalUsers(adminStatsRes.data.total_users);
      setTotalProperties(adminStatsRes.data.total_properties);
      setByCity(adminStatsRes.data.by_city || {});
      setByType(adminStatsRes.data.by_type || {});

      // 2. Market summary (avg price, avg price/sqft, active listings)
      const marketRes = await client.get("/analytics/market-summary");
      setMarketSummary(marketRes.data);

      // 3. Users list
      const usersRes = await client.get("/admin/users");
      setUsers(usersRes.data.users || []);

      // 4. All properties for status breakdown chart
      const propsRes = await client.get("/admin/properties");
      setAllProperties(propsRes.data.properties || []);

    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Compute status counts from real properties
  const statusCounts = allProperties.reduce((acc, p) => {
    const status = p.status || "unknown";
    acc[status] = (acc[status] || 0) + 1;
    return acc;
  }, {});
  const statusData = Object.entries(statusCounts).map(([status, count]) => ({
    name: status,
    count,
  }));

  // Convert by_city / by_type to chart data
  const cityData = Object.entries(byCity).map(([city, count]) => ({
    name: city,
    count,
  }));
  const typeData = Object.entries(byType).map(([type, count]) => ({
    name: type,
    count,
  }));

  const stats = [
    { label: "Total Users", value: totalUsers, Icon: Users },
    { label: "Total Listings", value: totalProperties, Icon: Building2 },
  ];

  if (loading) {
    return (
      <div className="p-6 md:p-8 space-y-8">
        <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[1, 2].map((i) => (
            <div key={i} className="border border-gray-200 rounded-xl p-4 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-1/4 mb-2" />
              <div className="h-8 bg-gray-200 rounded w-1/2" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 md:p-8 space-y-8">
        <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
        <div className="border border-red-200 bg-red-50 rounded-xl p-4 flex items-center gap-3 text-red-700">
          <AlertCircle size={20} className="shrink-0" />
          <span>{error}</span>
          <button
            onClick={loadData}
            className="ml-auto text-sm font-medium underline hover:text-red-800 flex items-center gap-1"
          >
            <RefreshCw size={14} /> Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 md:p-8 space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
      <Link
  to="/admin/properties"
  className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
>
  Review Pending Properties
</Link>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {stats.map(({ label, value, Icon }) => (
          <div
            key={label}
            className="border border-gray-200 rounded-xl p-4 flex items-center gap-3"
          >
            <div className="h-10 w-10 rounded-lg bg-blue-50 flex items-center justify-center">
              <Icon size={18} className="text-blue-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">{label}</p>
              <p className="text-xl font-bold text-gray-900">{value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Market Summary Section */}
      {marketSummary && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="border border-gray-200 rounded-xl p-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-emerald-50 flex items-center justify-center">
              <TrendingUp size={18} className="text-emerald-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Avg Property Price</p>
              <p className="text-xl font-bold text-gray-900">
                {new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(marketSummary.average_property_price)}
              </p>
            </div>
          </div>
          <div className="border border-gray-200 rounded-xl p-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-emerald-50 flex items-center justify-center">
              <TrendingUp size={18} className="text-emerald-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Avg Price / sqft</p>
              <p className="text-xl font-bold text-gray-900">
                {new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(marketSummary.average_price_per_sqft)}
              </p>
            </div>
          </div>
          <div className="border border-gray-200 rounded-xl p-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-blue-50 flex items-center justify-center">
              <Building2 size={18} className="text-blue-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Active Listings</p>
              <p className="text-xl font-bold text-gray-900">{marketSummary.active_listings}</p>
            </div>
          </div>
          <div className="border border-gray-200 rounded-xl p-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-blue-50 flex items-center justify-center">
              <Building2 size={18} className="text-blue-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Total Listings</p>
              <p className="text-xl font-bold text-gray-900">{marketSummary.total_listings}</p>
            </div>
          </div>
        </div>
      )}

      <div className="border border-gray-200 rounded-xl p-4">
        <h3 className="font-semibold text-gray-900 mb-3">
          Listings by Status (Platform-wide)
        </h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={statusData}>
            <XAxis dataKey="name" className="capitalize" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {statusData.map((entry) => (
                <Cell
                  key={entry.name}
                  fill={STATUS_COLORS[entry.name] || "#9ca3af"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* City & Type Breakdown Charts */}
      {(Object.keys(byCity).length > 0 || Object.keys(byType).length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="border border-gray-200 rounded-xl p-4">
            <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <MapPin size={16} className="text-blue-600" /> Listings by City
            </h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={cityData} layout="vertical">
                <XAxis type="number" allowDecimals={false} />
                <YAxis dataKey="name" type="category" width={100} />
                <Tooltip />
                <Bar dataKey="count" radius={[0, 4, 4, 0]} fill="#3b82f6">
                  {cityData.map((entry) => (
                    <Cell key={entry.name} fill="#3b82f6" />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="border border-gray-200 rounded-xl p-4">
            <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Home size={16} className="text-emerald-600" /> Listings by Type
            </h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={typeData} layout="vertical">
                <XAxis type="number" allowDecimals={false} />
                <YAxis dataKey="name" type="category" width={100} />
                <Tooltip />
                <Bar dataKey="count" radius={[0, 4, 4, 0]} fill="#10b981">
                  {typeData.map((entry) => (
                    <Cell key={entry.name} fill="#10b981" />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {users.length > 0 && (
          <div className="border border-gray-200 rounded-xl overflow-hidden">
            <h3 className="font-semibold text-gray-900 p-4 border-b border-gray-100 flex items-center justify-between">
              Users
              <span className="text-xs text-gray-500">{users.length} total</span>
            </h3>
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-3 font-medium text-gray-500">Name</th>
                  <th className="text-left p-3 font-medium text-gray-500">Email</th>
                  <th className="text-left p-3 font-medium text-gray-500">Role</th>
                  <th className="text-left p-3 font-medium text-gray-500">Verified</th>
                  <th className="text-left p-3 font-medium text-gray-500">Joined</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-t border-gray-100">
                    <td className="p-3 text-gray-900">{u.name}</td>
                    <td className="p-3 text-gray-700">{u.email}</td>
                    <td className="p-3 capitalize text-gray-700">{u.role}</td>
                    <td className="p-3">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${u.is_verified ? "bg-emerald-100 text-emerald-700" : "bg-gray-100 text-gray-500"}`}>
                        {u.is_verified ? "Yes" : "No"}
                      </span>
                    </td>
                    <td className="p-3 text-gray-500">{u.created_at ? new Date(u.created_at).toLocaleDateString() : "N/A"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}