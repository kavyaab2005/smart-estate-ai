import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  ImagePlus,
  X,
  ArrowLeft,
  Home,
  MapPin,
  Camera,
  IndianRupee,
} from "lucide-react";
import client from "../api/client";

const PROPERTY_TYPES = [
  { value: "apartment", label: "Apartment" },
  { value: "villa", label: "Villa" },
  { value: "Independent House", label: "Independent House" },
  { value: "plot", label: "Plot/Land" },
  // TODO: re-add once backend PropertyTypeEnum supports commercial and agricultural
];

const FURNISHING_OPTIONS = ["Unfurnished", "Semi-Furnished", "Fully Furnished"];

const initialForm = {
  title: "",
  description: "",
  property_type: "",
  listing_type: "buy",
  price: "",
  area_sqft: "",
  bhk: "",
  bathrooms: "",
  floor: "",
  total_floors: "",
  property_age_years: "",
  furnishing: "",
  parking: false,
  latitude: "",
  longitude: "",
  address: "",
  city: "",
  epid: "",
};

const inputClass =
  "w-full px-3.5 py-2.5 border border-gray-300 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all";
const labelClass = "block mb-1.5 text-sm font-medium text-gray-700";

const SECTION_THEMES = {
  blue: {
    iconBg: "bg-blue-50",
    iconColor: "text-blue-600",
    topBar: "bg-blue-500",
  },
  emerald: {
    iconBg: "bg-emerald-50",
    iconColor: "text-emerald-600",
    topBar: "bg-emerald-500",
  },
  amber: {
    iconBg: "bg-amber-50",
    iconColor: "text-amber-600",
    topBar: "bg-amber-500",
  },
};

function Section({ title, subtitle, icon: Icon, color, children }) {
  const theme = SECTION_THEMES[color];
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
      <div className={`h-1.5 ${theme.topBar}`} />
      <div className="p-6 space-y-5">
        <div className="flex items-center gap-3">
          <div
            className={`h-10 w-10 rounded-lg ${theme.iconBg} flex items-center justify-center shrink-0`}
          >
            <Icon size={18} className={theme.iconColor} />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{title}</h3>
            {subtitle && (
              <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>
            )}
          </div>
        </div>
        {children}
      </div>
    </div>
  );
}

export default function AddProperty() {
  const navigate = useNavigate();
  const [form, setForm] = useState(initialForm);
  const [images, setImages] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [createdProperty, setCreatedProperty] = useState(null);
  const [ownerName, setOwnerName] = useState("");
  const [surveyNumber, setSurveyNumber] = useState("");
  const [docType, setDocType] = useState("tax_receipt");
  const [docFile, setDocFile] = useState(null);
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const handleImageSelect = (e) => {
    const files = Array.from(e.target.files || []);
    const newImages = files.map((file) => ({
      file,
      previewUrl: URL.createObjectURL(file),
    }));
    setImages((prev) => [...prev, ...newImages]);
    e.target.value = "";
  };

  const removeImage = (index) => {
    setImages((prev) => {
      const updated = [...prev];
      URL.revokeObjectURL(updated[index].previewUrl);
      updated.splice(index, 1);
      return updated;
    });
  };

  const buildPayload = () => {
    const numericFields = [
      "price",
      "area_sqft",
      "bhk",
      "bathrooms",
      "floor",
      "total_floors",
      "property_age_years",
      "latitude",
      "longitude",
    ];

    const payload = { ...form };
    numericFields.forEach((field) => {
      if (payload[field] === "" || payload[field] === null) {
        delete payload[field];
      } else {
        payload[field] = Number(payload[field]);
      }
    });

    ["description", "property_type", "furnishing", "address", "city", "epid"].forEach(
      (field) => {
        if (payload[field] === "") delete payload[field];
      }
    );

    return payload;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!form.title.trim() || !form.price) {
      setError("Title and price are required.");
      return;
    }

    setSubmitting(true);
    try {
      const payload = buildPayload();
      const { data: newProperty } = await client.post("/properties", payload);

      for (const img of images) {
        const formData = new FormData();
        formData.append("file", img.file);
        await client.post(`/properties/${newProperty.id}/images`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }

      setCreatedProperty(newProperty);
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
        errorMessage = "Something went wrong while creating the property. Please try again.";
      }
      setError(errorMessage);
    } finally {
      setSubmitting(false);
    }
  };
    const [verifying, setVerifying] = useState(false);
  const [verifyError, setVerifyError] = useState("");
  const [verifyResult, setVerifyResult] = useState(null);

  const handleVerify = async () => {
    setVerifyError("");
    setVerifyResult(null);

    if (!ownerName.trim() || !surveyNumber.trim() || !docFile) {
      setVerifyError("Please enter owner name, survey number and choose a PDF.");
      return;
    }

    setVerifying(true);
    try {
      const uploadData = new FormData();
      uploadData.append("property_id", createdProperty.id);
      uploadData.append("doc_type", docType);
      uploadData.append("file", docFile);
      const { data: uploaded } = await client.post(
        "/documents/upload",
        uploadData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );

      const { data: result } = await client.post(
        `/documents/${uploaded.document_id}/verify`,
        {
          owner_name: ownerName.trim(),
          property_address: form.address || "",
          property_id: createdProperty.id,
          survey_number: surveyNumber.trim(),
          epid: createdProperty.epid || "",
          area: form.area_sqft ? `${form.area_sqft} sq ft` : "",
          document_date: "",
          registration_number: "",
        }
      );
      setVerifyResult(result);
    } catch (err) {
      console.error(err);
      const detail = err.response?.data?.detail;
      if (typeof detail === "string") {
        setVerifyError(detail);
      } else if (Array.isArray(detail)) {
        setVerifyError(
          detail
            .map((item) => `${(item.loc || []).slice(1).join(".")}: ${item.msg}`)
            .join("; ")
        );
      } else {
        setVerifyError("Could not verify the document. Please try again.");
      }
    } finally {
      setVerifying(false);
    }
  };
    if (createdProperty) {
    return (
      <div className="min-h-[calc(100vh-64px)] bg-gray-50">
        <div className="max-w-3xl mx-auto px-4 py-10">
          <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm space-y-4">
            <h1 className="text-2xl font-bold text-gray-900">
              Verify your documents
            </h1>
            <p className="text-sm text-gray-600">
              Your property was saved. Document upload comes next.
            </p>
                        <div>
              <label className={labelClass}>Owner name</label>
              <input
                type="text"
                value={ownerName}
                onChange={(e) => setOwnerName(e.target.value)}
                placeholder="As written on the documents"
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>Survey number</label>
              <input
                type="text"
                value={surveyNumber}
                onChange={(e) => setSurveyNumber(e.target.value)}
                placeholder="e.g. 231/8"
                className={inputClass}
              />
            </div>
                        <div>
              <label className={labelClass}>Document type</label>
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                className={inputClass}
              >
                <option value="tax_receipt">Property tax receipt</option>
                <option value="encumbrance_certificate">
                  Encumbrance certificate (EC)
                </option>
                <option value="khata_certificate">Khata certificate</option>
              </select>
            </div>
                        <div>
              <label className={labelClass}>Document (PDF)</label>
              <input
                type="file"
                accept="application/pdf"
                onChange={(e) => setDocFile(e.target.files?.[0] || null)}
                className={inputClass}
              />
              {docFile && (
                <p className="text-xs text-gray-500 mt-1.5">
                  Selected: {docFile.name}
                </p>
              )}
            </div>
                        {verifyError && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {verifyError}
              </div>
            )}
            <button
              type="button"
              onClick={handleVerify}
              disabled={verifying}
              className="bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-700 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium px-6 py-2.5 rounded-lg text-sm transition-all shadow-sm hover:shadow-md"
            >
              {verifying ? "Verifying..." : "Upload and verify"}
            </button>
                        {verifyResult && (
              <div className="border border-gray-200 rounded-lg p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-700">
                    Result:
                  </span>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-semibold ${
                      verifyResult.overall_status === "verified"
                        ? "bg-emerald-100 text-emerald-700"
                        : verifyResult.overall_status === "partial"
                        ? "bg-amber-100 text-amber-700"
                        : "bg-red-100 text-red-700"
                    }`}
                  >
                    {verifyResult.overall_status === "partial" ? "partly verified" : verifyResult.overall_status}
                  </span>
                </div>
                <ul className="space-y-1">
                  {verifyResult.match_results
                    .filter((r) => r.status === "match" || r.status === "mismatch")
                    .map((r) => (
                      <li
                        key={r.field}
                        className={`text-sm ${
                          r.status === "mismatch"
                            ? "text-red-700 font-medium"
                            : "text-gray-700"
                        }`}
                      >
                        {r.status === "match" ? "✓" : "✗"}{" "}
                        {r.field.replace(/_/g, " ")}: {r.status}
                      </li>
                    ))}
                </ul>
                {verifyResult.overall_status === "partial" && (
                  <p className="text-xs text-amber-700">
                    Some checks could not be done: {verifyResult.match_results
                      .filter((r) => r.status === "not_found" && ["owner_name", "survey_number", "epid"].includes(r.field))
                      .map((r) => r.field.replace(/_/g, " "))
                      .join(", ")}. Please check these manually.
                  </p>
                )}
                <p className="text-xs text-gray-500">{verifyResult.disclaimer}</p>
              </div>
            )}
            <Link
              to="/agent"
              className="inline-block text-sm text-gray-500 hover:text-gray-900"
            >
              Skip for now
            </Link>
          </div>
        </div>
      </div>
    );
  }
  return ( 
    
    <div className="min-h-[calc(100vh-64px)] bg-gray-50">
      {/* Gradient header banner */}
      <div className="bg-gradient-to-r from-indigo-600 via-blue-600 to-blue-500 text-white">
        <div className="max-w-3xl mx-auto px-4 pt-6 pb-10">
          <Link
            to="/agent"
            className="inline-flex items-center gap-1.5 text-sm text-blue-100 hover:text-white mb-4"
          >
            <ArrowLeft size={15} />
            Back to dashboard
          </Link>
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 rounded-xl bg-white/15 backdrop-blur flex items-center justify-center shrink-0">
              <Home size={22} />
            </div>
            <div>
              <h1 className="text-2xl font-bold">List Your Property</h1>
              <p className="text-sm text-blue-100 mt-0.5">
                Reach verified buyers — reviewed before it goes live.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 -mt-6 pb-10">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-6 shadow-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <Section
            title="Basic Details"
            icon={IndianRupee}
            color="blue"
          >
            <div>
              <label className={labelClass}>Title *</label>
              <input
                type="text"
                name="title"
                value={form.title}
                onChange={handleChange}
                required
                placeholder="e.g. 3BHK Modern Apartment in Koramangala"
                className={inputClass}
              />
            </div>

            <div>
              <label className={labelClass}>Description</label>
              <textarea
                name="description"
                value={form.description}
                onChange={handleChange}
                rows={4}
                placeholder="Describe the property — layout, condition, nearby landmarks..."
                className={inputClass}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelClass}>Property Type</label>
                <select
                  name="property_type"
                  value={form.property_type}
                  onChange={handleChange}
                  className={inputClass}
                >
                  <option value="">Select type</option>
                  {PROPERTY_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className={labelClass}>Listing Type *</label>
                <select
                  name="listing_type"
                  value={form.listing_type}
                  onChange={handleChange}
                  required
                  className={inputClass}
                >
                  <option value="buy">Sale</option>
                  <option value="rent">Rent</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelClass}>Price (₹) *</label>
                <input
                  type="number"
                  name="price"
                  value={form.price}
                  onChange={handleChange}
                  required
                  min="0"
                  placeholder="e.g. 9500000"
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Area (sqft)</label>
                <input
                  type="number"
                  name="area_sqft"
                  value={form.area_sqft}
                  onChange={handleChange}
                  min="0"
                  className={inputClass}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelClass}>Bedrooms (BHK)</label>
                <input
                  type="number"
                  name="bhk"
                  value={form.bhk}
                  onChange={handleChange}
                  min="0"
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Bathrooms</label>
                <input
                  type="number"
                  name="bathrooms"
                  value={form.bathrooms}
                  onChange={handleChange}
                  min="0"
                  className={inputClass}
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className={labelClass}>Floor</label>
                <input
                  type="number"
                  name="floor"
                  value={form.floor}
                  onChange={handleChange}
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Total Floors</label>
                <input
                  type="number"
                  name="total_floors"
                  value={form.total_floors}
                  onChange={handleChange}
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Property Age (yrs)</label>
                <input
                  type="number"
                  name="property_age_years"
                  value={form.property_age_years}
                  onChange={handleChange}
                  min="0"
                  className={inputClass}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 items-end">
              <div>
                <label className={labelClass}>Furnishing</label>
                <select
                  name="furnishing"
                  value={form.furnishing}
                  onChange={handleChange}
                  className={inputClass}
                >
                  <option value="">Select</option>
                  {FURNISHING_OPTIONS.map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
                </select>
              </div>
              <label className="flex items-center gap-2 text-sm text-gray-700 pb-2.5">
                <input
                  type="checkbox"
                  name="parking"
                  checked={form.parking}
                  onChange={handleChange}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                Parking available
              </label>
            </div>
          </Section>

          <Section title="Location" icon={MapPin} color="emerald">
            <div>
              <label className={labelClass}>Address</label>
              <input
                type="text"
                name="address"
                value={form.address}
                onChange={handleChange}
                className={inputClass}
              />
            </div>

            <div>
              <label className={labelClass}>City</label>
              <input
                type="text"
                name="city"
                value={form.city}
                onChange={handleChange}
                className={inputClass}
              />
            </div>

            <div>
              <label className={labelClass}>ePID (10-digit property ID)</label>
              <input type="text" inputMode="numeric" maxLength={10} pattern="\d{10}" name="epid" value={form.epid} onChange={handleChange} placeholder="e.g. 5196874965" className={inputClass} />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelClass}>Latitude</label>
                <input
                  type="number"
                  step="any"
                  name="latitude"
                  value={form.latitude}
                  onChange={handleChange}
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Longitude</label>
                <input
                  type="number"
                  step="any"
                  name="longitude"
                  value={form.longitude}
                  onChange={handleChange}
                  className={inputClass}
                />
              </div>
            </div>
          </Section>

          <Section
            title="Photos"
            subtitle="Add a few clear photos to help buyers picture the space."
            icon={Camera}
            color="amber"
          >
            <label
              htmlFor="image-upload"
              className="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-amber-300 bg-amber-50/40 rounded-lg py-8 cursor-pointer hover:border-amber-400 hover:bg-amber-50 transition-colors"
            >
              <ImagePlus size={22} className="text-amber-500" />
              <span className="text-sm text-amber-700 font-medium">
                Click to upload photos
              </span>
              <input
                id="image-upload"
                type="file"
                accept="image/*"
                multiple
                onChange={handleImageSelect}
                className="hidden"
              />
            </label>

            {images.length > 0 && (
              <div className="grid grid-cols-4 gap-3">
                {images.map((img, idx) => (
                  <div key={idx} className="relative group">
                    <img
                      src={img.previewUrl}
                      alt={`preview-${idx}`}
                      className="w-full h-24 object-cover rounded-lg border border-gray-200"
                    />
                    <button
                      type="button"
                      onClick={() => removeImage(idx)}
                      className="absolute -top-2 -right-2 h-6 w-6 rounded-full bg-red-600 text-white flex items-center justify-center text-xs shadow-sm hover:bg-red-700"
                      title="Remove"
                    >
                      <X size={13} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </Section>

          <div className="flex items-center gap-3 pt-2 pb-4">
            <button
              type="submit"
              disabled={submitting}
              className="bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-700 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium px-6 py-2.5 rounded-lg text-sm transition-all shadow-sm hover:shadow-md"
            >
              {submitting ? "Submitting..." : "Submit Property"}
            </button>
            <Link
              to="/agent"
              className="text-sm text-gray-500 hover:text-gray-900 px-4 py-2.5"
            >
              Cancel
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}