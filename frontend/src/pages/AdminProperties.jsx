import { Fragment, useState, useEffect } from "react";
import { CheckCircle2, XCircle, Building2, Loader2, AlertCircle, ShieldAlert, FileText } from "lucide-react";
import client from "../api/client";

const STATUS_TABS = ["pending", "approved", "rejected", "sold"];

const STATUS_BADGE = {
  pending: "bg-amber-100 text-amber-700",
  approved: "bg-green-100 text-green-700",
  rejected: "bg-gray-100 text-gray-500",
  sold: "bg-red-100 text-red-700",
};

const RISK_BADGE = {
  low: "bg-green-100 text-green-700",
  medium: "bg-yellow-100 text-yellow-700",
  high: "bg-red-100 text-red-700",
};

const DOC_STATUS_BADGE = {
  matched: "bg-green-100 text-green-700",
  mismatched: "bg-red-100 text-red-700",
  default: "bg-gray-100 text-gray-500",
};

function AdminProperties() {
  const [activeTab, setActiveTab] = useState("pending");
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actingId, setActingId] = useState(null);
  const [checksByPropertyId, setChecksByPropertyId] = useState({});
  const [loadingChecks, setLoadingChecks] = useState({});
  const [checkErrors, setCheckErrors] = useState({});

  const fetchProperties = async (status) => {
    setLoading(true);
    setError("");
    try {
      const { data } = await client.get("/admin/properties", { params: { status } });
      setProperties(data.properties || []);
    } catch (err) {
      console.error(err);
      setError("Couldn't load properties. Please refresh and try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProperties(activeTab);
  }, [activeTab]);

  const updateStatus = async (propertyId, newStatus) => {
    setActingId(propertyId);
    try {
      await client.put(`/admin/properties/${propertyId}/status`, { status: newStatus });
      setProperties((prev) => prev.filter((p) => p.id !== propertyId));
    } catch (err) {
      console.error(err);
      alert("Failed to update status. Please try again.");
    } finally {
      setActingId(null);
    }
  };

  const runChecks = async (property) => {
    const propertyId = property.id;
    setLoadingChecks((prev) => ({ ...prev, [propertyId]: true }));
    setCheckErrors((prev) => ({ ...prev, [propertyId]: null }));

    const fraudPayload = {
      property_id: property.id,
      property_type: property.property_type,
      listing_type: property.listing_type,
      price: Number(property.price),
      area_sqft: Number(property.area_sqft),
      bhk: Number(property.bhk),
      bedrooms: Number(property.bedrooms) || Number(property.bhk) || 0,
      floor: Number(property.floor) || 0,
      total_floors: Number(property.total_floors) || 1,
      property_age_years: Number(property.property_age_years) || 0,
      furnishing: property.furnishing || "unfurnished",
      parking: property.parking ? 1 : 0,
      city: property.city,
      amenities: property.amenities || [],
      is_verified: false,
    };
    const duplicatePayload = {
      property_id: property.id,
      title: property.title,
      description: property.description || "",
      city: property.city,
      price: Number(property.price),
      area_sqft: Number(property.area_sqft),
    };

    console.log("Fraud payload:", JSON.stringify(fraudPayload, null, 2));
    console.log("Duplicate payload:", JSON.stringify(duplicatePayload, null, 2));

    try {
      const [fraudRes, duplicateRes, docsRes] = await Promise.allSettled([
        client.post("/fraud/score", fraudPayload),
        client.post("/web-duplicate", duplicatePayload),
        client.get(`/documents/property/${propertyId}`),
      ]);

      const fraud = fraudRes.status === "fulfilled" ? fraudRes.value.data : null;
      const duplicate = duplicateRes.status === "fulfilled" ? duplicateRes.value.data : null;
      const docs = docsRes.status === "fulfilled" ? docsRes.value.documents : [];

      const extractErrorMessage = (error) => {
        if (!error) return null;
        // Axios error response format: error.response?.data?.detail (string or array)
        // FastAPI validation errors: error.response?.data?.detail is array of {loc, msg, type}
        const detail = error.response?.data?.detail;
        if (typeof detail === "string") return detail;
        if (Array.isArray(detail)) return detail.map(d => d.msg).join(", ");
        return "Unknown error";
      };

      const fraudError = fraudRes.status === "rejected" ? extractErrorMessage(fraudRes.reason) : null;
      const duplicateError = duplicateRes.status === "rejected" ? extractErrorMessage(duplicateRes.reason) : null;
      const docsError = docsRes.status === "rejected" ? extractErrorMessage(docsRes.reason) : null;

      setChecksByPropertyId((prev) => ({ ...prev, [propertyId]: { fraud, duplicate, docs } }));
      setCheckErrors((prev) => ({
        ...prev,
        [propertyId]: { fraud: fraudError, duplicate: duplicateError, docs: docsError },
      }));
    } finally {
      setLoadingChecks((prev) => ({ ...prev, [propertyId]: false }));
    }
  };

  const renderFraudCheck = (propertyId) => {
    const checks = checksByPropertyId[propertyId];
    const errors = checkErrors[propertyId];

    if (!checks?.fraud && !errors?.fraud) return null;

    return (
      <div className="bg-white rounded-lg border border-gray-200 p-3">
        <div className="flex items-center gap-2 mb-2">
          <ShieldAlert size={16} className="text-blue-600" />
          <span className="font-medium text-gray-900">Fraud Score</span>
          {errors?.fraud && <span className="text-xs text-red-500 ml-auto">Error: {errors.fraud}</span>}
        </div>
        {checks?.fraud ? (
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${RISK_BADGE[checks.fraud.risk_level] || RISK_BADGE.high}`}>
                {checks.fraud.risk_level?.toUpperCase()}
              </span>
              <span className="text-xs text-gray-500">Trust Score: {checks.fraud.trust_score}</span>
            </div>
            {checks.fraud.reasons?.length > 0 && (
              <ul className="list-disc list-inside text-xs text-gray-600 mt-1 ml-4">
                {checks.fraud.reasons.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            )}
          </div>
        ) : errors?.fraud ? (
          <p className="text-xs text-red-500">Failed to load fraud score</p>
        ) : null}
      </div>
    );
  };

  const renderDuplicateCheck = (propertyId) => {
    const checks = checksByPropertyId[propertyId];
    const errors = checkErrors[propertyId];

    if (!checks?.duplicate && !errors?.duplicate) return null;

    return (
      <div className="bg-white rounded-lg border border-gray-200 p-3">
        <div className="flex items-center gap-2 mb-2">
          <FileText size={16} className="text-purple-600" />
          <span className="font-medium text-gray-900">Duplicate Check</span>
          {errors?.duplicate && <span className="text-xs text-red-500 ml-auto">Error: {errors.duplicate}</span>}
        </div>
{checks?.duplicate ? (
                              <div className="flex items-center gap-2" key={`${propertyId}-duplicate`}>
                                {checks.duplicate.is_duplicate ? (
                                  <span key={`${propertyId}-dup-detected`} className="flex items-center gap-2">
                                    <AlertCircle size={14} className="text-red-500" />
                                    <span className="text-sm text-red-600 font-medium">
                                      Duplicate detected! {checks.duplicate.duplicates?.length || 0} similar listing(s) found
                                    </span>
                                  </span>
                                ) : (
                                  <span key={`${propertyId}-no-dup`} className="flex items-center gap-2">
                                    <CheckCircle2 size={14} className="text-green-500" />
                                    <span className="text-sm text-green-600 font-medium">No duplicates found</span>
                                  </span>
                                )}
                              </div>
                            ) : errors?.duplicate ? (
                              <p key={`${propertyId}-dup-error`} className="text-xs text-red-500">Failed to check duplicates</p>
                            ) : null}
      </div>
    );
  };

  const renderDocumentsCheck = (propertyId) => {
    const checks = checksByPropertyId[propertyId];
    const errors = checkErrors[propertyId];

    if (!checks?.docs && !errors?.docs) return null;

    return (
      <div className="bg-white rounded-lg border border-gray-200 p-3">
        <div className="flex items-center gap-2 mb-2">
          <FileText size={16} className="text-gray-600" />
          <span className="font-medium text-gray-900">Documents</span>
          {errors?.docs && <span className="text-xs text-red-500 ml-auto">Error: {errors.docs}</span>}
        </div>
        {checks?.docs?.length > 0 ? (
          <ul className="space-y-1">
            {checks.docs.map((doc) => (
              <li key={doc.document_id} className="flex items-center justify-between text-xs">
                <span className="text-gray-700">{doc.doc_type}</span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  DOC_STATUS_BADGE[doc.verification?.overall_status] || DOC_STATUS_BADGE.default
                }`}>
                  {doc.verification?.overall_status || "Not yet verified"}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-gray-500">No documents uploaded for this property</p>
        )}
      </div>
    );
  };

  const renderChecksRow = (propertyId) => {
    const hasChecks = checksByPropertyId[propertyId];
    if (!hasChecks) return null;

    return (
      <tr className="bg-gray-50 border-t border-gray-100">
        <td colSpan={7} className="p-4">
          <div className="space-y-3">
            {renderFraudCheck(propertyId)}
            {renderDuplicateCheck(propertyId)}
            {renderDocumentsCheck(propertyId)}
          </div>
        </td>
      </tr>
    );
  };

  return (
    <div className="p-6 md:p-8 space-y-6">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-lg bg-blue-50 flex items-center justify-center">
          <Building2 size={18} className="text-blue-600" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900">Property Verification</h1>
      </div>

      <div className="flex gap-2 border-b border-gray-200">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium capitalize border-b-2 transition-colors ${
              activeTab === tab
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-800"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {error && <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm">{error}</div>}

      {loading ? (
        <p className="text-gray-500 text-sm">Loading...</p>
      ) : properties.length === 0 ? (
        <div className="border border-gray-200 rounded-xl p-8 text-center text-gray-500">
          No {activeTab} properties right now.
        </div>
      ) : (
        <div className="border border-gray-200 rounded-xl overflow-hidden">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left p-3 font-medium text-gray-500">Title</th>
                <th className="text-left p-3 font-medium text-gray-500">Type</th>
                <th className="text-left p-3 font-medium text-gray-500">City</th>
                <th className="text-left p-3 font-medium text-gray-500">Price</th>
                <th className="text-left p-3 font-medium text-gray-500">Status</th>
                <th className="text-left p-3 font-medium text-gray-500">Submitted</th>
                <th className="text-left p-3 font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody>
              {properties.map((p) => (
                <Fragment key={p.id}>
                  <tr key={p.id} className="border-t border-gray-100">
                    <td className="p-3 text-gray-900">{p.title}</td>
                    <td className="p-3 text-gray-700 capitalize">{p.property_type || "-"} · {p.listing_type}</td>
                    <td className="p-3 text-gray-700">{p.city || "-"}</td>
                    <td className="p-3 text-gray-700">
                      {p.listing_type === "rent"
                        ? `₹${Number(p.price).toLocaleString("en-IN")}/mo`
                        : `₹${(p.price / 100000).toFixed(0)} L`}
                    </td>
                    <td className="p-3">
                      <span className={`text-xs font-medium capitalize px-2 py-0.5 rounded-full ${STATUS_BADGE[p.status]}`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="p-3 text-gray-500 text-xs">
                      {p.created_at ? new Date(p.created_at).toLocaleDateString() : "-"}
                    </td>
                    <td className="p-3">
                      {activeTab === "pending" ? (
                        <div className="flex gap-2 flex-wrap">
                          <button
                            className="flex items-center gap-1 text-blue-600 hover:text-blue-700 disabled:opacity-40 text-xs font-medium"
                            disabled={loadingChecks[p.id] || actingId === p.id}
                            onClick={() => runChecks(p)}
                          >
                            {loadingChecks[p.id] ? <Loader2 size={14} className="animate-spin" /> : <ShieldAlert size={14} />}
                            Run Checks
                          </button>
                          <button
                            className="flex items-center gap-1 text-green-600 hover:text-green-700 disabled:opacity-40 text-xs font-medium"
                            disabled={actingId === p.id}
                            onClick={() => updateStatus(p.id, "approved")}
                          >
                            <CheckCircle2 size={14} /> Approve
                          </button>
                          <button
                            className="flex items-center gap-1 text-red-600 hover:text-red-700 disabled:opacity-40 text-xs font-medium"
                            disabled={actingId === p.id}
                            onClick={() => updateStatus(p.id, "rejected")}
                          >
                            <XCircle size={14} /> Reject
                          </button>
                        </div>
                      ) : (
                        <span className="text-gray-300 text-xs">—</span>
                      )}
                    </td>
                  </tr>
                  {renderChecksRow(p.id)}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default AdminProperties;