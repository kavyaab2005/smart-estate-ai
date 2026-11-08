import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
  Legend,
} from "recharts";
import { Pencil, Trash2, Plus } from "lucide-react";
import client from "../api/client";

const STATUS_COLORS = {
  available: "#16a34a",
  approved: "#16a34a",
  sold: "#dc2626",
  pending: "#ca8a04",
  rejected: "#6b7280",
};

export default function AgentDashboard() {
  const navigate = useNavigate();
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState(null);

  // Inquiries state
  const [inquiries, setInquiries] = useState([]);
  const [inquiriesLoading, setInquiriesLoading] = useState(true);
  const [inquiriesError, setInquiriesError] = useState(null);
  const [updatingInquiryId, setUpdatingInquiryId] = useState(null);

  const fetchListings = async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await client.get("/properties/mine");
      setListings(data.properties || []);
    } catch (err) {
      console.error(err);
      setError("Couldn't load your live listings.");
    } finally {
      setLoading(false);
    }
  };

  const fetchInquiries = async () => {
    setInquiriesLoading(true);
    setInquiriesError(null);
    try {
      const res = await client.get("/inquiries/agent");
      setInquiries(res.data || []);
    } catch (err) {
      console.error(err);
      const detail = err.response?.data?.detail;
      let errorMessage;
      if (typeof detail === "string") {
        errorMessage = detail;
      } else if (Array.isArray(detail)) {
        errorMessage = detail
          .map((item) => `${(item.loc || []).slice(1).join(".")}: ${item.msg}`)
          .join("; ");
      } else {
        errorMessage = "Could not load inquiries.";
      }
      setInquiriesError(errorMessage);
    } finally {
      setInquiriesLoading(false);
    }
  };

  const updateInquiryStatus = async (id, statusValue) => {
    setUpdatingInquiryId(id);
    setInquiriesError(null);
    try {
      await client.put(`/inquiries/${id}/status`, null, { params: { status_value: statusValue } });
      setInquiries((prev) =>
        prev.map((inq) => (inq.id === id ? { ...inq, status: statusValue } : inq))
      );
    } catch (err) {
      console.error(err);
      const detail = err.response?.data?.detail;
      let errorMessage;
      if (typeof detail === "string") {
        errorMessage = detail;
      } else if (Array.isArray(detail)) {
        errorMessage = detail
          .map((item) => `${(item.loc || []).slice(1).join(".")}: ${item.msg}`)
          .join("; ");
      } else {
        errorMessage = "Could not update inquiry status.";
      }
      setInquiriesError(errorMessage);
    } finally {
      setUpdatingInquiryId(null);
    }
  };

  const formatVisitTime = (iso) => {
    if (!iso) return "Not specified";
    const hasOffset = iso.endsWith("Z") || iso.includes("+");
    const utcString = hasOffset ? iso : `${iso}Z`;
    return new Date(utcString).toLocaleString("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "Asia/Kolkata",
    });
  };

  useEffect(() => {
    fetchListings();
  }, []);

  useEffect(() => {
    fetchInquiries();
  }, []);

  const handleDelete = async (property, title) => {
    const confirmed = window.confirm(
      `Delete "${title}"? This cannot be undone.`
    );
    if (!confirmed) return;

    setDeletingId(property.id);
    try {
      await client.delete(`/properties/${property.id}`);
      setListings((prev) => prev.filter((p) => p.id !== property.id));
    } catch (err) {
      console.error(err);
      alert("Failed to delete this listing. Please try again.");
    } finally {
      setDeletingId(null);
    }
  };

  const statusCounts = listings.reduce((acc, p) => {
    acc[p.status] = (acc[p.status] || 0) + 1;
    return acc;
  }, {});
  const statusData = Object.entries(statusCounts).map(([status, count]) => ({
    name: status,
    value: count,
  }));

  const priceData = [...listings]
    .sort((a, b) => a.price - b.price)
    .map((p) => ({
      name: p.title.length > 18 ? p.title.slice(0, 18) + "…" : p.title,
      price: p.price / 100000, // in lakhs, for readable axis labels
    }));

  return (
    <div className="p-6 md:p-8 space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Agent Dashboard</h1>
        <Link
          to="/agent/add-property"
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
        >
          <Plus size={16} />
          Add Property
        </Link>
      </div>

      {error && (
        <div className="bg-yellow-50 text-yellow-800 p-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Visit & Inquiry Requests */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900">Visit & Inquiry Requests</h2>
          <span className="px-3 py-1 text-sm font-medium bg-amber-100 text-amber-800 rounded-full">
            {inquiries.filter((i) => i.status === "pending").length} pending
          </span>
        </div>

        {inquiriesError && (
          <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
            {inquiriesError}
          </div>
        )}

        {inquiriesLoading ? (
          <p className="text-gray-500 text-sm">Loading requests...</p>
        ) : inquiries.length === 0 ? (
          <div className="border border-gray-200 rounded-xl p-8 text-center text-gray-500">
            No requests yet. Buyers' visit and inquiry requests will appear here.
          </div>
        ) : (
          <div className="space-y-4">
            {inquiries.map((inq) => {
              const isUpdating = updatingInquiryId === inq.id;
              const isPending = inq.status === "pending";
              const isConfirmed = inq.status === "confirmed";
              const isFinal = inq.status === "completed" || inq.status === "cancelled";

              const typeLabel = {
                schedule_visit: "Visit request",
                general: "General question",
                price_negotiation: "Price discussion",
              }[inq.inquiry_type] || inq.inquiry_type;

              const statusColors = {
                pending: "bg-amber-100 text-amber-800",
                confirmed: "bg-emerald-100 text-emerald-800",
                completed: "bg-gray-100 text-gray-800",
                cancelled: "bg-red-100 text-red-800",
              };

              return (
                <div key={inq.id} className="border border-gray-200 rounded-xl p-4 space-y-3">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h3 className="font-semibold text-gray-900">
                        {inq.property_title || "Property"}
                      </h3>
                      <p className="text-sm text-gray-500">{inq.property_city || "Unknown location"}</p>
                    </div>
                    <span className={`px-3 py-1 text-xs font-medium rounded-full ${statusColors[inq.status] || "bg-gray-100 text-gray-800"}`}>
                      {inq.status.charAt(0).toUpperCase() + inq.status.slice(1)}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm text-gray-700">
                    <div>
                      <span className="font-medium text-gray-500">Buyer: </span>
                      <a href={`mailto:${inq.buyer_email}`} className="text-emerald-600 hover:underline">
                        {inq.buyer_name || "Unknown"} ({inq.buyer_email})
                      </a>
                    </div>
                    <div>
                      <span className="font-medium text-gray-500">Type: </span>
                      {typeLabel}
                    </div>
                  </div>

                  {inq.inquiry_type === "schedule_visit" && (
                    <p className="text-sm text-gray-600">
                      <span className="font-medium text-gray-500">Preferred time: </span>
                      {formatVisitTime(inq.preferred_date)}
                    </p>
                  )}

                  {inq.message && (
                    <p className="text-sm text-gray-600 italic border-l-2 border-gray-200 pl-3">
                      &ldquo;{inq.message}&rdquo;
                    </p>
                  )}

                  {!isFinal && (
                    <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
                      {isPending && (
                        <>
                          <button
                            onClick={() => updateInquiryStatus(inq.id, "confirmed")}
                            disabled={isUpdating}
                            className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {isUpdating ? "Updating..." : "Confirm"}
                          </button>
                          <button
                            onClick={() => updateInquiryStatus(inq.id, "cancelled")}
                            disabled={isUpdating}
                            className="flex-1 border-2 border-red-600 text-red-600 hover:bg-red-50 font-medium py-2 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            Decline
                          </button>
                        </>
                      )}
                      {isConfirmed && (
                        <>
                          <button
                            onClick={() => updateInquiryStatus(inq.id, "completed")}
                            disabled={isUpdating}
                            className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {isUpdating ? "Updating..." : "Mark completed"}
                          </button>
                          <button
                            onClick={() => updateInquiryStatus(inq.id, "cancelled")}
                            disabled={isUpdating}
                            className="flex-1 border-2 border-red-600 text-red-600 hover:bg-red-50 font-medium py-2 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            Cancel
                          </button>
                        </>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {loading ? (
        <p className="text-gray-500 text-sm">Loading your listings...</p>
      ) : listings.length === 0 ? (
        <div className="text-center text-gray-500 py-12 border border-gray-200 rounded-xl space-y-4">
          <p>No listings yet.</p>
          <Link to="/agent/add-property" className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">
            <Plus size={16} />
            Add Your First Property
          </Link>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="border border-gray-200 rounded-xl p-4">
              <h3 className="font-semibold text-gray-900 mb-3">
                Listings by Status
              </h3>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={statusData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label
                  >
                    {statusData.map((entry) => (
                      <Cell
                        key={entry.name}
                        fill={STATUS_COLORS[entry.name] || "#9ca3af"}
                      />
                    ))}
                  </Pie>
                  <Legend />
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="border border-gray-200 rounded-xl p-4">
              <h3 className="font-semibold text-gray-900 mb-3">
                Price by Listing (₹ Lakhs)
              </h3>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={priceData}>
                  <XAxis dataKey="name" hide />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="price" fill="#2563eb" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="border border-gray-200 rounded-xl overflow-hidden">
            <h3 className="font-semibold text-gray-900 p-4 border-b border-gray-100">
              My Listings
            </h3>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left p-3 font-medium text-gray-500">
                      Title
                    </th>
                    <th className="text-left p-3 font-medium text-gray-500">
                      Price
                    </th>
                    <th className="text-left p-3 font-medium text-gray-500">
                      BHK
                    </th>
                    <th className="text-left p-3 font-medium text-gray-500">
                      Status
                    </th>
                    <th className="text-left p-3 font-medium text-gray-500">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {listings.map((p) => (
                    <tr key={p.id} className="border-t border-gray-100">
                      <td className="p-3 text-gray-900">{p.title}</td>
                      <td className="p-3 text-gray-700">
                        {p.listing_type === "rent"
    ? `₹${Number(p.price).toLocaleString("en-IN")}/mo`
    : `₹${(p.price / 100000).toFixed(0)} L`}
                      </td>
                      <td className="p-3 text-gray-700">{p.bhk ?? "-"}</td>
                      <td className="p-3 capitalize text-gray-700">
                        {p.status}
                      </td>
                      <td className="p-3">
                        <div className="flex gap-2">
                          <button
                            className="text-gray-400 hover:text-blue-600"
                            onClick={() => navigate(`/agent/edit-property/${p.id}`)}
                          >
                            <Pencil size={14} />
                          </button>
                          <button
                            className="text-gray-400 hover:text-red-600 disabled:opacity-30"
                            disabled={deletingId === p.id}
                            onClick={() => handleDelete(p, p.title)}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}