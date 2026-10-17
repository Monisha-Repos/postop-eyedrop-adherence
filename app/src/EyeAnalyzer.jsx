
import { useEffect, useState } from "react";

export default function EyeAnalyzer({ api }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!file) {
      setPreview("");
      return;
    }

    const url = URL.createObjectURL(file);
    setPreview(url);

    return () => URL.revokeObjectURL(url);
  }, [file]);

  function handleFileChange(event) {
    const selected = event.target.files?.[0];

    setResult(null);
    setError("");

    if (!selected) {
      setFile(null);
      return;
    }

    const allowed = [
      "image/jpeg",
      "image/png",
      "image/webp"
    ];

    if (!allowed.includes(selected.type)) {
      setError("Please select a JPG, PNG or WebP image.");
      setFile(null);
      return;
    }

    if (selected.size > 5 * 1024 * 1024) {
      setError("Image must be smaller than 5 MB.");
      setFile(null);
      return;
    }

    setFile(selected);
  }

  async function handleAnalyze() {
    if (!file || loading) return;

    setLoading(true);
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("image", file);

    try {
      // Reuse the existing authenticated API client.
      // This requires api.post to support FormData.
      const data = await api.post(
        "/analyze-eye",
        formData
      );

      setResult(data.analysis);
    } catch (err) {
      setError(err.message || "Analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section
      style={{
        padding: 24,
        marginTop: 20,
        border: "1px solid #ddd",
        borderRadius: 12
      }}
    >
      <h2>EyeSpy AI — Eye Image Analyzer</h2>

      <p>
        Upload an eye photo to receive an
        AI-generated description of visible features.
      </p>

      <input
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onChange={handleFileChange}
        aria-label="Upload eye image"
      />

      {preview && (
        <img
          src={preview}
          alt="Uploaded eye preview"
          style={{
            display: "block",
            width: "100%",
            maxHeight: 300,
            objectFit: "contain",
            marginTop: 20,
            borderRadius: 10
          }}
        />
      )}

      <button
        type="button"
        onClick={handleAnalyze}
        disabled={!file || loading}
        style={{
          padding: "12px 24px",
          marginTop: 20,
          background: "#2563eb",
          color: "white",
          border: "none",
          borderRadius: 8,
          cursor: !file || loading
            ? "not-allowed"
            : "pointer"
        }}
      >
        {loading ? "Analyzing Eye..." : "Analyze Eye"}
      </button>

      {error && (
        <p role="alert" style={{ color: "#dc2626" }}>
          {error}
        </p>
      )}

      {result && (
        <div
          style={{
            textAlign: "left",
            marginTop: 24,
            padding: 20,
            borderRadius: 12,
            background: "#f3f4f6",
            color: "#111827"
          }}
        >
          <h3>Gemini AI Analysis</h3>

          {[
            ["Redness", result.redness],
            ["Irritation", result.irritation],
            ["Cloudiness", result.cloudiness],
            ["Image Quality", result.image_quality],
            ["Summary", result.summary],
            ["Recommendation", result.recommendation]
          ].map(([label, value]) => (
            <p key={label}>
              <strong>{label}: </strong>
              {value || "Not assessed"}
            </p>
          ))}

          <p style={{ fontSize: 12 }}>
            EyeSpy AI is an educational prototype,
            not a medical diagnostic tool.
            Sudden vision changes, vision loss,
            or severe eye pain require urgent
            medical attention.
          </p>
        </div>
      )}
    </section>
  );
}
