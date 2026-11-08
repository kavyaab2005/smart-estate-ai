import { useState, useEffect } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
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

const emptyForm = {
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
  blue: { iconBg: "bg-blue-50", iconColor: "text-blue-600", topBar: "bg-blue-500" },
  emerald: { iconBg: "bg-emerald-50", iconColor: "text-emerald-600", topBar: "bg-emerald-500" },
  amber: { iconBg: "bg-amber-50", iconColor: "text-amber-600", topBar: "bg-amber-500" },
};

function Section({ title, subtitle, icon: Icon, color, children }) {
  const theme = SECTION_THEMES[color];
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
      <div className={`h-1.5 ${theme.topBar}`} />
      <div className="p-6 space-y-5">
        <div className="flex items-center gap-3">
          <div className={`h-10 w-10 rounded-lg ${theme.iconBg} flex items-center justify-center shrink-0`}>
            <Icon size={18} className={theme.iconColor} />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{title}</h3>
            {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
          </div>
        </div>
        {children}
      </div>
    </div>
  );
}

const EDITABLE_FIELDS = Object.keys(emptyForm);

export default function EditProperty() {
  const navigate = useNavigate();
  const { propertyId } = useParams();

  const [form, setForm] = useState(emptyForm);
  const [existingImages, setExistingImages] = useState([]);
  const [newImages, setNewImages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    const fetchProperty = async () => {
      setLoading(true);
      setError("");
      try {
        const { data } = await client.get(`/properties/${propertyId}`);
        const prop = data.property;

        const filled = {};
        EDITABLE_FIELDS.forEach((field) => {
          const val = prop[field];
          filled[field] = val === null || val === undefined ? emptyForm[field] : val;
        });
        setForm(filled);
        setExistingImages(data.images || []);
      } catch (err) {
        console.error(err);
        if (err.response?.status === 404) {
          setNotFound(true);
        } else {
          setError("Couldn't load this property. Please go back and try again.");
        }
      } finally {
        setLoading(false);
      }
    };
    fetchProperty();
  }, [propertyId]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const handleImageSelect = (e) => {
    const files = Array.from(e.target.files || []);
    const added = files.map((file) => ({
      file,
      previewUrl: URL.createObjectURL(file),
    }));
    setNewImages((prev) => [...prev, ...added]);
    e.target.value = "";
  };

  const removeNewImage = (index) => {
    setNewImages((prev) => {
      const updated = [...prev];
      URL.revokeObjectURL(updated[index].previewUrl);
      updated.splice(index, 1);
      return updated;
    });
  };

  const buildPayload = () => {
    const numericFields = [
      "price", "area_sqft", "bhk", "bathrooms", "floor",
      "total_floors", "property_age_years", "latitude", "longitude",
    ];
    const payload = { ...form };
    numericFields.forEach((field) => {
      if (payload[field] === "" || payload[field] === null) {
        delete payload[field];
      } else {
        payload[field] = Number(payload[field]);
      }
    });
    ["description", "property_type", "furnishing", "address", "city"].forEach((field) => {
      if (payload[field] === "") delete payload[field];
    });
    payload.epid = payload.epid || null;
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
      await client.put(`/properties/${propertyId}`, payload);

      for (const img of newImages) {
        const formData = new FormData();
        formData.append("file", img.file);
        await client.post(`/properties/${propertyId}/images`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }

      navigate("/agent");
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
        errorMessage = "Something went wrong while saving. Please try again.";
      }
      setError(errorMessage);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[calc(100vh-64px)] bg-gray-50 flex items-center justify-center">
        <p className="text-sm text-gray-500">Loading property...</p>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="min-h-[calc(100vh-64px)] bg-gray-50 flex flex-col items-center justify-center gap-3">
        <p className="text-gray-700 font-medium">Property not found.</p>
        <Link to="/agent" className="text-sm text-blue-600 hover:underline">
          Back to dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-64px)] bg-gray-50">
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
              <h1 className="text-2xl font-bold">Edit Property</h1>
              <p className="text-sm text-blue-100 mt-0.5">
                Update the details below and save your changes.
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
          <Section title="Basic Details" icon={IndianRupee} color="blue">
            <div>
              <label className={labelClass}>Title *</label>
              <input
                type="text"
                name="title"
                value={form.title}
                onChange={handleChange}
                required
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
                    <option key={t.value} value={t.value}>{t.label}</option>
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
                    <option key={f} value={f}>{f}</option>
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
            subtitle="Existing photos are shown below. Add more if you'd like."
            icon={Camera}
            color="amber"
          >
            {existingImages.length > 0 && (
              <div>
                <p className="text-xs font-medium text-gray-500 mb-2">Current photos</p>
                <div className="grid grid-cols-4 gap-3">
                  {existingImages.map((url, idx) => (
                    <img
                      key={idx}
                      src={url.startsWith("http") ? url : `http://127.0.0.1:8000${url}`}
                      alt={`existing-${idx}`}
                      className="w-full h-24 object-cover rounded-lg border border-gray-200"
                    />
                  ))}
                </div>
              </div>
            )}

            <label
              htmlFor="image-upload"
              className="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-amber-300 bg-amber-50/40 rounded-lg py-8 cursor-pointer hover:border-amber-400 hover:bg-amber-50 transition-colors"
            >
              <ImagePlus size={22} className="text-amber-500" />
              <span className="text-sm text-amber-700 font-medium">
                Click to add more photos
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

            {newImages.length > 0 && (
              <div>
                <p className="text-xs font-medium text-gray-500 mb-2">New photos to add</p>
                <div className="grid grid-cols-4 gap-3">
                  {newImages.map((img, idx) => (
                    <div key={idx} className="relative group">
                      <img
                        src={img.previewUrl}
                        alt={`new-${idx}`}
                        className="w-full h-24 object-cover rounded-lg border border-gray-200"
                      />
                      <button
                        type="button"
                        onClick={() => removeNewImage(idx)}
                        className="absolute -top-2 -right-2 h-6 w-6 rounded-full bg-red-600 text-white flex items-center justify-center text-xs shadow-sm hover:bg-red-700"
                        title="Remove"
                      >
                        <X size={13} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Section>

          <div className="flex items-center gap-3 pt-2 pb-4">
            <button
              type="submit"
              disabled={submitting}
              className="bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-700 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium px-6 py-2.5 rounded-lg text-sm transition-all shadow-sm hover:shadow-md"
            >
              {submitting ? "Saving..." : "Save Changes"}
            </button>
            <Link to="/agent" className="text-sm text-gray-500 hover:text-gray-900 px-4 py-2.5">
              Cancel
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}