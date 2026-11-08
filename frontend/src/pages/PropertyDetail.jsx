import { useState, useEffect } from "react";
import { MapPin, BedDouble, Bath, Square, Phone, ShieldCheck, TrendingUp, AlertCircle, CheckCircle, Loader2, DollarSign, ArrowUpRight, Building2, HeartPulse, Train, Bus, ShoppingBag, Utensils, Trees, MapPin as MapPinIcon, Star, Calculator, RefreshCw, Leaf, X } from "lucide-react";
import { useParams, Link, useNavigate } from "react-router-dom";
import client from "../api/client";

const EPID_PORTAL_URL = "https://gbaeaasthi.karnataka.gov.in/citizen/citizenIntroduction";

export default function PropertyDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [activeImage, setActiveImage] = useState(0);
  const [epidCopied, setEpidCopied] = useState(null);

  const [property, setProperty] = useState(null);
  const [images, setImages] = useState([]);
  const [amenities, setAmenities] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  // Analysis tab state
  const [activeTab, setActiveTab] = useState("overview"); // overview | analysis | forecast | location | emi
  const [analysisData, setAnalysisData] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState(null);

  // Forecast tab state
  const [forecastData, setForecastData] = useState(null);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [forecastError, setForecastError] = useState(null);

  // Sustainability tab state
  const [sustainabilityData, setSustainabilityData] = useState(null);
  const [sustainabilityLoading, setSustainabilityLoading] = useState(false);
  const [sustainabilityError, setSustainabilityError] = useState(null);

  // Location tab state
  const [locationData, setLocationData] = useState(null);
  const [locationLoading, setLocationLoading] = useState(false);
  const [locationError, setLocationError] = useState(null);

  // EMI tab state
  const [emiData, setEmiData] = useState(null);
  const [emiLoading, setEmiLoading] = useState(false);
  const [emiError, setEmiError] = useState(null);
  // EMI input state (user-adjustable)
  const [emiInputs, setEmiInputs] = useState({
    down_payment_percent: 20,
    interest_rate_annual: 6.5,
    loan_tenure_years: 20,
    estimated_monthly_rent: 0,
  });

  // Inquiry modal state
  const [showInquiryModal, setShowInquiryModal] = useState(false);
  const [inquiryForm, setInquiryForm] = useState({
    inquiry_type: "schedule_visit",
    message: "",
    preferred_date: "",
  });
  const [inquirySubmitting, setInquirySubmitting] = useState(false);
  const [inquiryError, setInquiryError] = useState(null);
  const [inquirySuccess, setInquirySuccess] = useState(false);

  useEffect(() => {
    async function loadProperty() {
      setIsLoading(true);
      try {
        const res = await client.get(`/properties/${id}`);
        if (res.data?.property) {
          setProperty(res.data.property);
          setImages(res.data.images || []);
          setAmenities(res.data.amenities || []);

          // Fetch trust signals if not included in response
          if (!res.data.property.trust_signals) {
            try {
              const signalsRes = await client.get(`/properties/${id}/trust-signals`);
              if (signalsRes.data?.trust_signals) {
                setProperty(prev => ({ ...prev, trust_signals: signalsRes.data.trust_signals }));
              }
            } catch {
              // trust signals optional
            }
          }
        } else {
          setProperty(null);
        }
      } catch (err) {
        console.error("Failed to load property", err);
        setProperty(null);
      } finally {
        setIsLoading(false);
      }
    }
    loadProperty();
  }, [id]);

  // Analysis tab loader
  const loadAnalysis = async () => {
    if (analysisData) return; // already loaded
    setAnalysisLoading(true);
    setAnalysisError(null);
    try {
      const res = await client.get(`/properties/${id}/analyze`);
      setAnalysisData(res.data);
    } catch (err) {
      setAnalysisError(err.response?.data?.detail || "Failed to load analysis");
    } finally {
      setAnalysisLoading(false);
    }
  };

  // Forecast tab loader
  const loadForecast = async () => {
    if (forecastData) return; // already loaded
    if (!property) return;
    setForecastLoading(true);
    setForecastError(null);
    try {
      const res = await client.post("/forecasting/predict", {
        current_price: property.price,
        city: property.city || "default",
        years: 5,
      });
      setForecastData(res.data);
    } catch (err) {
      setForecastError(err.response?.data?.detail || "Failed to load forecast");
    } finally {
      setForecastLoading(false);
    }
  };

  // Sustainability tab loader
  const loadSustainability = async () => {
    if (sustainabilityData) return;
    if (!property) return;
    if (!property.area_sqft) {
      setSustainabilityError("Area is not listed for this property, so a sustainability estimate isn't available.");
      return;
    }
    setSustainabilityLoading(true);
    setSustainabilityError(null);
    try {
      const res = await client.post("/sustainability/evaluate", {
        area_sqft: Number(property.area_sqft),
        total_floors: property.total_floors || 1,
        parking: Boolean(property.parking),
      });
      setSustainabilityData(res.data);
    } catch (err) {
      setSustainabilityError(err.response?.data?.detail || "Failed to load sustainability estimate");
    } finally {
      setSustainabilityLoading(false);
    }
  };

  // Location tab loader
  const loadLocation = async () => {
    if (locationData) return; // already loaded
    setLocationLoading(true);
    setLocationError(null);
    try {
      const res = await client.get(`/properties/${id}/location-intel`);
      setLocationData(res.data);
    } catch (err) {
      setLocationError(err.response?.data?.detail || "Failed to load location intelligence");
    } finally {
      setLocationLoading(false);
    }
  };

  // EMI tab loader
  const loadEmi = async () => {
    if (!property) return;
    setEmiLoading(true);
    setEmiError(null);
    try {
      const res = await client.post("/financials/calculate-mortgage", {
        property_price: property.price,
        down_payment_percent: emiInputs.down_payment_percent,
        interest_rate_annual: emiInputs.interest_rate_annual,
        loan_tenure_years: emiInputs.loan_tenure_years,
        estimated_monthly_rent: emiInputs.estimated_monthly_rent,
      });
      setEmiData(res.data);
    } catch (err) {
      setEmiError(err.response?.data?.detail || "Failed to calculate EMI");
    } finally {
      setEmiLoading(false);
    }
  };

  // Handle EMI input change - debounced recalculation

  const handleInquirySubmit = async (e) => {
    e.preventDefault();
    setInquirySubmitting(true);
    setInquiryError(null);
    try {
      await client.post("/inquiries/", {
        property_id: property.id,
        inquiry_type: inquiryForm.inquiry_type,
        message: inquiryForm.message || null,
        preferred_date: inquiryForm.preferred_date ? new Date(inquiryForm.preferred_date).toISOString() : null,
      });
      setInquirySuccess(true);
    } catch (err) {
      if (err.response?.status === 401) {
        setInquiryError("Please log in as a buyer to contact the seller.");
      } else {
        setInquiryError(err.response?.data?.detail || "Could not send your request.");
      }
    } finally {
      setInquirySubmitting(false);
    }
  };

  const closeInquiryModal = () => {
    setShowInquiryModal(false);
    setInquiryForm({ inquiry_type: "schedule_visit", message: "", preferred_date: "" });
    setInquiryError(null);
    setInquirySuccess(false);
  };
  const handleEmiInputChange = (field, value) => {
    setEmiInputs(prev => ({ ...prev, [field]: value }));
  };

  if (isLoading) {
    return <div className="p-8 text-center text-gray-500">Loading property details...</div>;
  }

  if (!property) {
    return (
      <div className="p-8 text-center text-gray-500">
        Property not found. <Link to="/search" className="text-blue-600 underline">Back to search</Link>
      </div>
    );
  }

  const formattedPrice = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(property.price);

  return (
    <>
    <div className="p-6 md:p-8 max-w-6xl mx-auto space-y-8 animate-fade-in-up">
      {/* Image gallery */}
      <div>
        <div className="h-80 w-full bg-gray-100 rounded-xl overflow-hidden flex items-center justify-center">
          {images.length > 0 ? (
            <img
              src={images[activeImage]}
              alt={property.title}
              className="h-full w-full object-cover"
            />
          ) : (
            <span className="text-gray-400 text-sm">No image available</span>
          )}
        </div>
        {images.length > 1 && (
          <div className="flex gap-2 mt-2">
            {images.map((img, i) => (
              <button
                key={i}
                onClick={() => setActiveImage(i)}
                className={`h-16 w-16 rounded-lg overflow-hidden border-2 cursor-pointer ${
                  i === activeImage ? "border-blue-600" : "border-transparent"
                }`}
              >
                <img
                  src={img}
                  alt={`${property.title} ${i + 1}`}
                  className="h-full w-full object-cover"
                />
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left: main details */}
        <div className="lg:col-span-2 space-y-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {property.title}
            </h1>
            <p className="flex items-center gap-1 text-gray-500 mt-1">
              <MapPin size={16} className="shrink-0" />
              {property.address}
            </p>
            <button
              onClick={() => navigate(`/map?selected=${property?.id || id}`)}
              className="ml-2 p-1.5 text-gray-400 hover:text-blue-600 hover:bg-gray-100 rounded-lg transition-colors"
              title="View on Map"
              aria-label="View on Map"
            >
              <MapPin size={16} />
            </button>
            {property.epid && (
              <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-gray-700">
                <span>ePID: {property.epid}</span>
                <button onClick={() => navigator.clipboard.writeText(property.epid)} className="px-2 py-1 border rounded text-xs">Copy ePID</button>
                <a href={EPID_PORTAL_URL} target="_blank" rel="noopener noreferrer" onClick={() => { navigator.clipboard.writeText(property.epid).then(() => setEpidCopied(true)).catch(() => setEpidCopied(false)); }} className="px-2 py-1 bg-indigo-600 text-white rounded text-xs">Verify on official portal</a>
              {epidCopied === true && <p className="basis-full text-xs text-gray-500">ePID copied. On the portal, open Search Property and paste it.</p>}
              {epidCopied === false && <p className="basis-full text-xs text-gray-500">Could not copy automatically. Copy the ePID above, then on the portal open Search Property and paste it.</p>}
              </div>
            )}
          </div>

          <p className="text-3xl font-bold text-gray-900">
            {formattedPrice}
          </p>

          <div className="flex items-center gap-6 text-gray-700 border-y border-gray-100 py-3">
            <span className="flex items-center gap-1.5">
              <BedDouble size={18} />
              {property.bhk ?? "—"} BHK
            </span>
            <span className="flex items-center gap-1.5">
              <Bath size={18} />
              {property.bathrooms ?? "—"} Bath
            </span>
            <span className="flex items-center gap-1.5">
              <Square size={18} />
              {property.area_sqft === null || property.area_sqft === undefined || property.area_sqft === "" || isNaN(Number(property.area_sqft)) || Number(property.area_sqft) <= 0
                ? "—"
                : `${Number(property.area_sqft).toLocaleString("en-IN")} sq. ft.`}
            </span>
          </div>

          {amenities.length > 0 && (
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Amenities</h3>
              <div className="flex flex-wrap gap-2">
                {amenities.map((a) => (
                  <span
                    key={a}
                    className="px-3 py-1 rounded-full bg-gray-100 text-sm text-gray-700"
                  >
                    {a}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Tab Navigation */}
          <div className="border-b border-gray-200">
            <nav className="flex gap-6" aria-label="Property insights">
              <button
                onClick={() => setActiveTab("overview")}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === "overview"
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                Overview
              </button>
              <button
                onClick={() => { setActiveTab("analysis"); loadAnalysis(); }}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === "analysis"
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                Analysis
              </button>
              <button
                onClick={() => { setActiveTab("forecast"); loadForecast(); }}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === "forecast"
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                Forecast
              </button>
              <button
                onClick={() => { setActiveTab("location"); loadLocation(); }}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === "location"
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                Location
              </button>
              <button
                onClick={() => { setActiveTab("emi"); loadEmi(); }}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === "emi"
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                EMI Calculator
              </button>
              <button
                onClick={() => { setActiveTab("sustainability"); loadSustainability(); }}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === "sustainability"
                    ? "border-emerald-600 text-emerald-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                Sustainability
              </button>
            </nav>
          </div>

          {/* Analysis Tab Content */}
          {activeTab === "analysis" && (
            <div className="space-y-6 animate-fade-in-up">
              {analysisLoading && (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                  <span className="ml-3 text-gray-600">Loading analysis...</span>
                </div>
              )}
              {analysisError && (
                <div className="p-4 rounded-lg bg-red-50 border border-red-200 flex items-center gap-3 text-red-700">
                  <AlertCircle size={20} className="shrink-0" />
                  <span>{analysisError}</span>
                  <button
                    onClick={loadAnalysis}
                    className="ml-auto text-sm font-medium underline hover:text-red-800"
                  >
                    Retry
                  </button>
                </div>
              )}
              {analysisData && !analysisLoading && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Property Analysis Scores</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {[
                        { label: "Price", score: analysisData.price_score, icon: TrendingUp },
                        { label: "Location", score: analysisData.location_score, icon: TrendingUp },
                        { label: "Amenities", score: analysisData.amenity_score, icon: TrendingUp },
                        { label: "Market", score: analysisData.market_price_score, icon: TrendingUp },
                      ].map((item, i) => (
                        item.score != null && (
                          <div key={i} className="p-4 rounded-xl bg-gray-50 border border-gray-100 text-center">
                            <item.icon size={24} className="mx-auto mb-2 text-blue-600" />
                            <p className="text-2xl font-bold text-gray-900">{item.score}</p>
                            <p className="text-xs text-gray-500 mt-1">{item.label} Score</p>
                          </div>
                        )
                      ))}
                    </div>
                  </div>

                  {analysisData.document_score != null && (
                    <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
                      <h4 className="font-medium text-gray-900 mb-2">Document & Risk Scores</h4>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                        {analysisData.document_score != null && (
                          <div className="flex items-center gap-2">
                            <CheckCircle className="text-emerald-600" size={16} />
                            <span>Document Score: <strong>{analysisData.document_score}</strong></span>
                          </div>
                        )}
                        {analysisData.fraud_score != null && (
                          <div className="flex items-center gap-2">
                            <AlertCircle className={analysisData.fraud_score > 50 ? "text-red-600" : "text-emerald-600"} size={16} />
                            <span>Fraud Risk: <strong>{analysisData.fraud_score}</strong></span>
                          </div>
                        )}
                        {analysisData.requirement_match_score != null && (
                          <div className="flex items-center gap-2">
                            <CheckCircle className="text-blue-600" size={16} />
                            <span>Requirement Match: <strong>{analysisData.requirement_match_score}</strong></span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  <div className="p-4 rounded-xl bg-blue-50 border border-blue-100">
                    <h4 className="font-medium text-blue-900 mb-2">AI Recommendation</h4>
                    <p className="text-blue-800 text-sm leading-relaxed">{analysisData.recommendation_text}</p>
                  </div>

                  <div className="text-center pt-4">
                    <div className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gray-900 text-white">
                      <TrendingUp size={20} />
                      <span className="text-lg font-semibold">Overall Score: {analysisData.overall_score} / 100</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Forecast Tab Content */}
          {activeTab === "forecast" && (
            <div className="space-y-6 animate-fade-in-up">
              {forecastLoading && (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                  <span className="ml-3 text-gray-600">Loading forecast...</span>
                </div>
              )}
              {forecastError && (
                <div className="p-4 rounded-lg bg-red-50 border border-red-200 flex items-center gap-3 text-red-700">
                  <AlertCircle size={20} className="shrink-0" />
                  <span>{forecastError}</span>
                  <button
                    onClick={loadForecast}
                    className="ml-auto text-sm font-medium underline hover:text-red-800"
                  >
                    Retry
                  </button>
                </div>
              )}
              {forecastData && !forecastLoading && (
                <div className="space-y-6">
                  <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold text-gray-900">Price Forecast</h3>
                      <span className="text-sm text-gray-500">
                        Assumed annual growth: <strong>{forecastData.assumed_annual_growth_rate}</strong>
                      </span>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      <div className="p-4 rounded-lg bg-white border border-gray-100 text-center">
                        <p className="text-xs text-gray-500 mb-1">Current Price</p>
                        <p className="text-2xl font-bold text-gray-900">
                          {new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(forecastData.current_price)}
                        </p>
                      </div>
                      <div className="p-4 rounded-lg bg-white border border-gray-100 text-center">
                        <p className="text-xs text-gray-500 mb-1">Projected Price (Year 5)</p>
                        <p className="text-2xl font-bold text-blue-600">
                          {new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(forecastData.price_after_5_years)}
                        </p>
                      </div>
                      <div className="p-4 rounded-lg bg-white border border-gray-100 text-center">
                        <p className="text-xs text-gray-500 mb-1">Total Appreciation</p>
                        <p className="text-2xl font-bold text-emerald-600 flex items-center justify-center gap-1">
                          <ArrowUpRight size={20} />
                          {new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(forecastData.total_expected_appreciation)}
                        </p>
                      </div>
                    </div>
                  </div>

                  {forecastData.projections && forecastData.projections.length > 0 && (
                    <div>
                      <h4 className="font-medium text-gray-900 mb-3">Yearly Projections</h4>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                          <thead>
                            <tr className="border-b border-gray-200">
                              <th className="pb-2 font-medium text-gray-500">Year</th>
                              <th className="pb-2 font-medium text-gray-500">Projected Price</th>
                              <th className="pb-2 font-medium text-gray-500">Est. ROI</th>
                            </tr>
                          </thead>
                          <tbody>
                            {forecastData.projections.map((p) => (
                              <tr key={p.year} className="border-b border-gray-100 hover:bg-gray-50">
                                <td className="py-3 font-medium text-gray-900">Year {p.year}</td>
                                <td className="py-3 text-gray-700">
                                  {new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(p.projected_price)}
                                </td>
                                <td className="py-3 text-emerald-600 font-medium">
                                  +{p.estimated_roi_percent}%
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  <div className="p-4 rounded-xl bg-blue-50 border border-blue-100">
                    <h4 className="font-medium text-blue-900 mb-2">Methodology</h4>
                    <p className="text-blue-800 text-sm">
                      Projections based on historical appreciation rates for <strong>{forecastData.city}</strong>.
                      Actual returns may vary based on market conditions, infrastructure development, and economic factors.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Location Tab Content */}
          {activeTab === "location" && (
            <div className="space-y-6 animate-fade-in-up">
              {locationLoading && (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                  <span className="ml-3 text-gray-600">Loading location intelligence...</span>
                </div>
              )}
              {locationError && (
                <div className="p-4 rounded-lg bg-red-50 border border-red-200 flex items-center gap-3 text-red-700">
                  <AlertCircle size={20} className="shrink-0" />
                  <span>{locationError}</span>
                  <button
                    onClick={loadLocation}
                    className="ml-auto text-sm font-medium underline hover:text-red-800"
                  >
                    Retry
                  </button>
                </div>
              )}
              {locationData && !locationLoading && (
                <div className="space-y-6">
                  <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold text-gray-900">Location Intelligence</h3>
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        locationData.data_source === "live"
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-amber-100 text-amber-700"
                      }`}>
                        {locationData.data_source === "live" ? "Live OSM Data" : "Fallback Data"}
                      </span>
                    </div>
                    <div className="text-center py-4">
                      <div className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gray-900 text-white">
                        <Star size={20} />
                        <span className="text-lg font-semibold">Location Score: {locationData.location_score} / 100</span>
                      </div>
                    </div>
                  </div>

                  {locationData.nearby && (
                    <div className="space-y-6">
                      {Object.entries(locationData.nearby).map(([category, places]) => {
                        if (!places || places.length === 0) return null;
                        const icons = {
                          schools: Building2,
                          hospitals: HeartPulse,
                          metro: Train,
                          bus_stops: Bus,
                          malls: ShoppingBag,
                          restaurants: Utensils,
                          parks: Trees,
                        };
                        const labels = {
                          schools: "Schools",
                          hospitals: "Hospitals",
                          metro: "Metro Stations",
                          bus_stops: "Bus Stops",
                          malls: "Shopping Malls",
                          restaurants: "Restaurants",
                          parks: "Parks",
                        };
                        const Icon = icons[category] || MapPinIcon;
                        return (
                          <div key={category} className="p-4 rounded-xl bg-white border border-gray-100">
                            <div className="flex items-center gap-2 mb-3">
                              <Icon size={20} className="text-blue-600" />
                              <h4 className="font-medium text-gray-900 capitalize">{labels[category] || category}</h4>
                              <span className="text-xs text-gray-500">({places.length})</span>
                            </div>
                            <ul className="space-y-2">
                              {places.slice(0, 5).map((place, idx) => (
                                <li key={`${category}-${idx}`} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                                  <div className="flex items-center gap-3">
                                    <span className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center text-xs font-medium text-gray-600">{idx + 1}</span>
                                    <span className="text-sm text-gray-700">{place.name}</span>
                                  </div>
                                  <span className="text-xs text-gray-500 flex items-center gap-1">
                                    <MapPinIcon size={12} />
                                    {place.distance_km} km
                                  </span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  <div className="p-4 rounded-xl bg-blue-50 border border-blue-100">
                    <h4 className="font-medium text-blue-900 mb-2">About This Data</h4>
                    <p className="text-blue-800 text-sm">
                      Nearby facilities sourced from OpenStreetMap via Overpass API (2 km radius).
                      {locationData.data_source === "fallback" && " Live data unavailable; showing representative fallback data for major cities. "}
                      Distances are straight-line from property coordinates. Location score considers facility count and proximity across categories.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* EMI Calculator Tab Content */}
          {activeTab === "emi" && (
            <div className="space-y-6 animate-fade-in-up">
              {emiLoading && !emiData && (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                  <span className="ml-3 text-gray-600">Calculating EMI...</span>
                </div>
              )}
              {emiError && (
                <div className="p-4 rounded-lg bg-red-50 border border-red-200 flex items-center gap-3 text-red-700">
                  <AlertCircle size={20} className="shrink-0" />
                  <span>{emiError}</span>
                  <button
                    onClick={loadEmi}
                    className="ml-auto text-sm font-medium underline hover:text-red-800"
                  >
                    Retry
                  </button>
                </div>
              )}
              {(!emiLoading || emiData) && (
                <div className="space-y-6">
                  {/* Input Form */}
                  <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                        <Calculator size={20} /> EMI Calculator
                      </h3>
                      {emiData && (
                        <button
                          onClick={loadEmi}
                          className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1"
                        >
                          <RefreshCw size={14} /> Recalculate
                        </button>
                      )}
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                      <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">Down Payment %</label>
                        <input
                          type="number"
                          min="0"
                          max="100"
                          step="1"
                          value={emiInputs.down_payment_percent}
                          onChange={(e) => handleEmiInputChange("down_payment_percent", parseFloat(e.target.value) || 0)}
                          className="w-full px-3 py-2 rounded-lg border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">Interest Rate % (Annual)</label>
                        <input
                          type="number"
                          min="0"
                          max="20"
                          step="0.1"
                          value={emiInputs.interest_rate_annual}
                          onChange={(e) => handleEmiInputChange("interest_rate_annual", parseFloat(e.target.value) || 0)}
                          className="w-full px-3 py-2 rounded-lg border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">Loan Tenure (Years)</label>
                        <input
                          type="number"
                          min="1"
                          max="30"
                          step="1"
                          value={emiInputs.loan_tenure_years}
                          onChange={(e) => handleEmiInputChange("loan_tenure_years", parseInt(e.target.value) || 1)}
                          className="w-full px-3 py-2 rounded-lg border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">Est. Monthly Rent (₹)</label>
                        <input
                          type="number"
                          min="0"
                          step="1000"
                          value={emiInputs.estimated_monthly_rent}
                          onChange={(e) => handleEmiInputChange("estimated_monthly_rent", parseFloat(e.target.value) || 0)}
                          className="w-full px-3 py-2 rounded-lg border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Results */}
                  {emiData && (
                    <div className="space-y-6">
                      <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
                        <h4 className="font-medium text-gray-900 mb-4">Loan Summary</h4>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                          <div className="p-4 rounded-lg bg-white border border-gray-100 text-center">
                            <p className="text-xs text-gray-500 mb-1">Property Price</p>
                            <p className="text-xl font-bold text-gray-900">
                              {new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(emiData.property_price)}
                            </p>
                          </div>
                          <div className="p-4 rounded-lg bg-white border border-gray-100 text-center">
                            <p className="text-xs text-gray-500 mb-1">Down Payment ({emiInputs.down_payment_percent}%)</p>
                            <p className="text-xl font-bold text-gray-700">
                              {new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(emiData.down_payment)}
                            </p>
                          </div>
                          <div className="p-4 rounded-lg bg-white border border-gray-100 text-center">
                            <p className="text-xs text-gray-500 mb-1">Loan Amount</p>
                            <p className="text-xl font-bold text-blue-600">
                              {new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(emiData.loan_amount)}
                            </p>
                          </div>
                        </div>
                      </div>

                      <div className="p-4 rounded-xl bg-blue-50 border border-blue-100">
                        <h4 className="font-medium text-blue-900 mb-4 flex items-center gap-2">
                          <Calculator size={20} /> Monthly EMI Breakdown
                        </h4>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          <div className="p-4 rounded-lg bg-white border border-gray-100 text-center">
                            <p className="text-xs text-gray-500 mb-1">Monthly EMI</p>
                            <p className="text-2xl font-bold text-blue-600">
                              {new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(emiData.monthly_emi)}
                            </p>
                          </div>
                          <div className="p-4 rounded-lg bg-white border border-gray-100 text-center">
                            <p className="text-xs text-gray-500 mb-1">Total Interest</p>
                            <p className="text-xl font-bold text-red-600">
                              {new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(emiData.total_interest_payable)}
                            </p>
                          </div>
                          <div className="p-4 rounded-lg bg-white border border-gray-100 text-center">
                            <p className="text-xs text-gray-500 mb-1">Total Payable</p>
                            <p className="text-xl font-bold text-gray-900">
                              {new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(emiData.total_amount_payable)}
                            </p>
                          </div>
                          <div className="p-4 rounded-lg bg-white border border-gray-100 text-center">
                            <p className="text-xs text-gray-500 mb-1">Gross Rental Yield</p>
                            <p className="text-xl font-bold text-emerald-600">
                              {emiData.gross_rental_yield_percent.toFixed(2)}%
                            </p>
                          </div>
                        </div>
                      </div>

                      <div className="p-4 rounded-xl bg-amber-50 border border-amber-100">
                        <h4 className="font-medium text-amber-900 mb-2">Key Insights</h4>
                        <ul className="space-y-1 text-sm text-amber-800">
                          <li>• Loan covers <strong>{((emiData.loan_amount / emiData.property_price) * 100).toFixed(1)}%</strong> of property value</li>
                          <li>• Total interest is <strong>{((emiData.total_interest_payable / emiData.loan_amount) * 100).toFixed(1)}%</strong> of loan amount over {emiInputs.loan_tenure_years} years</li>
                          {emiInputs.estimated_monthly_rent > 0 && (
                            <li>• At ₹{new Intl.NumberFormat("en-IN").format(emiInputs.estimated_monthly_rent)}/month rent, gross yield is <strong>{emiData.gross_rental_yield_percent.toFixed(2)}%</strong> annually</li>
                          )}
                          <li>• EMI assumes fixed interest rate for entire tenure; actual rates may vary</li>
                        </ul>
                      </div>
                    </div>
)}
        </div>
      )}
    </div>
          )}

          {/* Sustainability Tab Content */}
          {activeTab === "sustainability" && (
            <div className="space-y-6 animate-fade-in-up">
              {sustainabilityLoading && (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
                  <span className="ml-3 text-gray-600">Loading sustainability estimate...</span>
                </div>
              )}
              {sustainabilityError && (
                <div className="p-4 rounded-lg bg-red-50 border border-red-200 flex items-center gap-3 text-red-700">
                  <AlertCircle size={20} className="shrink-0" />
                  <span>{sustainabilityError}</span>
                  <button
                    onClick={loadSustainability}
                    className="ml-auto text-sm font-medium underline hover:text-red-800"
                  >
                    Retry
                  </button>
                </div>
              )}
              {sustainabilityData && !sustainabilityLoading && (
                <div className="space-y-6">
                  <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                        <Leaf size={20} className="text-emerald-600" /> Sustainability Estimate
                      </h3>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="p-4 rounded-lg bg-white border border-gray-100 text-center">
                        <p className="text-xs text-gray-500 mb-1">Rooftop Solar Capacity</p>
                        <p className="text-2xl font-bold text-emerald-600">
                          {sustainabilityData.estimated_rooftop_solar_capacity_kw} kW
                        </p>
                      </div>
                      <div className="p-4 rounded-lg bg-white border border-gray-100 text-center">
                        <p className="text-xs text-gray-500 mb-1">Annual Solar Generation</p>
                        <p className="text-2xl font-bold text-emerald-600">
                          {new Intl.NumberFormat("en-IN").format(sustainabilityData.estimated_annual_solar_generation_kwh)} kWh
                        </p>
                      </div>
                      <div className="p-4 rounded-lg bg-white border border-gray-100 text-center">
                        <p className="text-xs text-gray-500 mb-1">CO₂ Reduction</p>
                        <p className="text-2xl font-bold text-emerald-600">
                          {sustainabilityData.co2_reduction_tons_per_year} tons/year
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-100">
                    <div className="flex items-center gap-4">
                      <div className="p-2 rounded-lg bg-emerald-100 text-emerald-700">
                        <Leaf size={20} />
                      </div>
                      <div>
                        <p className="font-medium text-emerald-900">
                          Green rating: <strong>{sustainabilityData.green_rating}</strong>
                        </p>
                        <p className="text-emerald-700">
                          Sustainability score: <strong>{sustainabilityData.sustainability_score}/100</strong>
                        </p>
                      </div>
                    </div>
                    <p className="text-xs text-emerald-600 mt-2">
                      Estimates based on roof area, floors and parking. Indicative only.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Legal Verification Banner & Entry Point */}
          <div className="p-4 rounded-xl border border-emerald-200 bg-emerald-50/50 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-emerald-100 text-emerald-700">
                <ShieldCheck size={20} />
              </div>
              <div>
                <h4 className="font-semibold text-emerald-900 text-sm">
                  Document Intelligence & Title Verification
                </h4>
                <p className="text-xs text-emerald-700">
                  Inspect extracted OCR fields, fuzzy title matching, and check encumbrance status.
                </p>
              </div>
            </div>
            <Link
              to={`/verify-documents?propertyId=${property.id}`}
              className="text-xs font-semibold px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors whitespace-nowrap shadow-xs"
            >
              Verify Documents Tab →
            </Link>
          </div>
        </div>

        {/* Right: contact seller */}
        <div className="space-y-4">
          <div className="p-4 border border-gray-200 rounded-xl bg-white space-y-3 shadow-xs">
            <h3 className="font-semibold text-gray-900">Contact Seller</h3>
            <button
              onClick={() => setShowInquiryModal(true)}
              className="w-full flex items-center justify-center gap-2 bg-clay hover:bg-clay-dark text-ink rounded-lg py-2 text-sm font-medium cursor-pointer"
            >
              <Phone size={16} />
              Contact Seller
            </button>
            <p className="text-xs text-gray-400 text-center">
              Contact details are shared once you reach out.
            </p>
          </div>
        </div>
      </div>
    </div>

    {/* Inquiry Modal */}
    {showInquiryModal && (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 animate-fade-in-up"
        onClick={closeInquiryModal}
        role="dialog"
        aria-modal="true"
        aria-labelledby="inquiry-modal-title"
      >
        <div
          className="w-full max-w-md bg-white rounded-2xl shadow-xl overflow-hidden animate-fade-in-up"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between p-4 border-b border-gray-100">
            <h2 id="inquiry-modal-title" className="font-serif text-lg font-semibold text-ink">
              {inquirySuccess ? "Request Sent" : "Contact Seller"}
            </h2>
            <button
              onClick={closeInquiryModal}
              className="p-1 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100"
              aria-label="Close"
            >
              <X size={20} />
            </button>
          </div>

          {inquirySuccess ? (
            <div className="p-6 text-center space-y-4">
              <div className="mx-auto w-16 h-16 rounded-full bg-clay/10 flex items-center justify-center">
                <CheckCircle size={28} className="text-clay" />
              </div>
              <p className="text-sage">Request sent. The agent will get back to you.</p>
              <button
                onClick={closeInquiryModal}
                className="w-full bg-clay hover:bg-clay-dark text-ink font-medium py-2 px-4 rounded-lg transition-colors"
              >
                Close
              </button>
            </div>
          ) : (
            <form onSubmit={handleInquirySubmit} className="p-4 space-y-4">
              {inquiryError && (
                <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
                  {inquiryError}
                </div>
              )}

              <div>
                <label htmlFor="inquiry-type" className="block mb-1 text-sm font-medium text-gray-700">
                  Inquiry Type
                </label>
                <select
                  id="inquiry-type"
                  value={inquiryForm.inquiry_type}
                  onChange={(e) => setInquiryForm((prev) => ({ ...prev, inquiry_type: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-clay focus:border-transparent"
                >
                  <option value="schedule_visit">Schedule a visit</option>
                  <option value="general">General question</option>
                  <option value="price_negotiation">Discuss price</option>
                </select>
              </div>

              <div>
                <label htmlFor="inquiry-message" className="block mb-1 text-sm font-medium text-gray-700">
                  Message (optional)
                </label>
                <textarea
                  id="inquiry-message"
                  value={inquiryForm.message}
                  onChange={(e) => setInquiryForm((prev) => ({ ...prev, message: e.target.value }))}
                  rows={3}
                  placeholder="Any specific questions or details..."
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-clay focus:border-transparent"
                />
              </div>

              {inquiryForm.inquiry_type === "schedule_visit" && (
                <div>
                  <label htmlFor="inquiry-date" className="block mb-1 text-sm font-medium text-gray-700">
                    Preferred Date & Time
                  </label>
                  <input
                    id="inquiry-date"
                    type="datetime-local"
                    value={inquiryForm.preferred_date}
                    onChange={(e) => setInquiryForm((prev) => ({ ...prev, preferred_date: e.target.value }))}
                    min={new Date().toISOString().slice(0, 16)}
                    className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-clay focus:border-transparent"
                  />
                </div>
              )}

              <button
                type="submit"
                disabled={inquirySubmitting}
                className="w-full bg-clay hover:bg-clay-dark text-ink font-medium py-2 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {inquirySubmitting ? "Sending..." : "Send Request"}
              </button>
            </form>
          )}
</div>
    </div>
    )}
    </>
  );
}