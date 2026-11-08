import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Upload, FileText, Loader2 } from "lucide-react";
import DocumentChecklist from "../components/DocumentChecklist";
import client from "../api/client";

export default function DocumentVerification() {
  const [searchParams] = useSearchParams();
  const propertyId = searchParams.get("propertyId");
  const [selectedFile, setSelectedFile] = useState(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [docType, setDocType] = useState("tax_receipt");

  function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setResult(null);
      setError(null);
    }
  }

  async function handleVerify() {
    if (!selectedFile) return;
    setIsVerifying(true);
    setError(null);
    try {
      // 1. Upload document
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("property_id", propertyId || "");
      formData.append("doc_type", docType);
      
      const uploadRes = await client.post("/documents/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const documentId = uploadRes.data.document_id;

      // 2. Verify document
      const verifyRes = await client.post(`/documents/${documentId}/verify`);
      setResult(verifyRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Verification failed. Please try again.");
    } finally {
      setIsVerifying(false);
    }
  }

  return (
    <div className="p-6 md:p-8 max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">
        Document Verification
      </h1>

      {propertyId && (
        <p className="text-sm text-gray-500">
          Verifying document for property: <code className="bg-gray-100 px-1.5 py-0.5 rounded">{propertyId}</code>
        </p>
      )}

      <div className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center space-y-3">
        <Upload size={28} className="mx-auto text-gray-400" />
        <div>
          <label
            htmlFor="document-upload-input"
            className="inline-block cursor-pointer text-sm font-medium text-blue-600 hover:text-blue-700"
          >
            Choose a file to upload
            <input
              id="document-upload-input"
              name="document"
              type="file"
              accept=".pdf,.jpg,.jpeg,.png"
              className="hidden"
              onChange={handleFileChange}
            />
          </label>
          <p className="text-xs text-gray-400 mt-1">
            PDF, JPG, or PNG accepted
          </p>
        </div>

        {selectedFile && (
          <div className="flex items-center justify-center gap-2 text-sm text-gray-700 bg-gray-50 rounded-lg px-3 py-2">
            <FileText size={14} />
            {selectedFile.name}
          </div>
        )}
      </div>

      <div className="space-y-3">
        <select
          value={docType}
          onChange={(e) => setDocType(e.target.value)}
          className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="sale_deed">Sale Deed</option>
          <option value="title_deed">Title Deed</option>
          <option value="encumbrance_certificate">Encumbrance Certificate</option>
          <option value="khata_certificate">Khata Certificate</option>
          <option value="property_tax_receipt">Property Tax Receipt</option>
          <option value="approved_plan">Approved Plan</option>
          <option value="other">Other</option>
        </select>

        <button
          onClick={handleVerify}
          disabled={!selectedFile || isVerifying}
          className="w-full bg-blue-600 text-white rounded-lg py-2.5 text-sm font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isVerifying && <Loader2 size={16} className="animate-spin" />}
          {isVerifying ? "Verifying..." : "Verify Document"}
        </button>
      </div>

      {error && (
        <p className="text-sm text-red-600 text-center bg-red-50 p-3 rounded-lg">
          {error}
        </p>
      )}

      {result && (
        <DocumentChecklist
          matchResults={result.match_results}
          overallStatus={result.overall_status}
          disclaimer={result.disclaimer}
        />
      )}
    </div>
  );
}