
import { useEffect, useState } from "react";

const buttonStyle = {
  padding: "12px 24px",
  marginTop: 20,
  marginRight: 10,
  background: "#2563eb",
  color: "white",
  border: "none",
  borderRadius: 8,
  cursor: "pointer"
};

const disclaimer =
  "EyeSpy AI is an educational prototype, not a medical diagnostic tool. " +
  "Sudden vision changes, vision loss, or severe eye pain require urgent medical attention.";

function AnalysisDetails({ analysis }) {
  let data = analysis;

  if (typeof data === "string") {
    try {
      data = JSON.parse(data);
    } catch {
      return <p style={{ whiteSpace: "pre-wrap" }}>{data}</p>;
    }
  }

  if (!data || typeof data !== "object") {
    return <p>No analysis details available.</p>;
  }

  return (
    <div>
      {[
        ["Redness", data.redness],
        ["Irritation", data.irritation],
        ["Cloudiness", data.cloudiness],
        ["Image Quality", data.image_quality],
        ["Summary", data.summary],
        ["Recommendation", data.recommendation]
      ].map(([label, value]) => (
        <p key={label}>
          <strong>{label}: </strong>
          {typeof value === "string"
            ? value || "Not assessed"
            : value == null
              ? "Not assessed"
              : JSON.stringify(value)}
        </p>
      ))}

      <p style={{ fontSize: 12, marginTop: 20 }}>
        {disclaimer}
      </p>
    </div>
  );
}

function SavedEyePhoto({ api, analysisId }) {
  const [imageUrl, setImageUrl] = useState("");
  const [imageError, setImageError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let objectUrl = "";

    async function loadPhoto() {
      try {
        const blob = await api.blob(
          `/eye-analysis-history/${analysisId}/image`
        );

        if (cancelled) return;

        objectUrl = URL.createObjectURL(blob);
        setImageUrl(objectUrl);
      } catch (err) {
        if (!cancelled) {
          setImageError(true);
        }
      }
    }

    loadPhoto();

    return () => {
      cancelled = true;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [api, analysisId]);

  if (imageError) {
    return (
      <p style={{ color: "#6b7280" }}>
        No saved photo available for this entry.
      </p>
    );
  }

  if (!imageUrl) {
    return <p>Loading photo...</p>;
  }

  return (
    <img
      src={imageUrl}
      alt={`Saved eye photo ${analysisId}`}
      style={{
        display: "block",
        width: "100%",
        maxWidth: 320,
        maxHeight: 240,
        objectFit: "contain",
        borderRadius: 10,
        marginTop: 12,
        marginBottom: 12
      }}
    />
  );
}

export default function EyeAnalyzer({ api }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");

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

  async function loadHistory() {
    setHistoryLoading(true);
    setHistoryError("");

    try {
      const data = await api.get("/eye-analysis-history");
      setHistory(data.history || []);
    } catch (err) {
      setHistoryError(
        err.message || "Could not load analysis history."
      );
    } finally {
      setHistoryLoading(false);
    }
  }

  async function handleToggleHistory() {
    if (showHistory) {
      setShowHistory(false);
      return;
    }

    setShowHistory(true);
    await loadHistory();
  }

  async function handleSavePhoto() {
  if (!file || loading) return;

  setLoading(true);
  setError("");
  setResult(null);

  const formData = new FormData();
  formData.append("image", file);

  try {
    const data = await api.post(
      "/save-eye-photo",
      formData
    );

    if (data.success) {
      alert("Eye photo saved successfully!");

      // Refresh history if it is visible
      if (showHistory) {
        await loadHistory();
      }
    }
  } catch (err) {
    setError(err.message || "Could not save eye photo.");
  } finally {
    setLoading(false);
  }
}

  async function handleAnalyze() {
    if (!file || loading) return;

    setLoading(true);
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("image", file);

    try {
      const data = await api.post(
        "/analyze-eye",
        formData
      );

      setResult(data.analysis);

      // Refresh saved results if history is open.
      if (showHistory) {
        await loadHistory();
      }
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

      <div>
        <button
          type="button"
          onClick={handleAnalyze}
          disabled={!file || loading}
          style={{
            ...buttonStyle,
            opacity: !file || loading ? 0.6 : 1,
            cursor: !file || loading
              ? "not-allowed"
              : "pointer"
          }}
        >
          {loading ? "Analyzing Eye..." : "Analyze Eye"}
        </button>

        <button
          type="button"
          onClick={handleSavePhoto}
          disabled={!file || loading}
          style={{
            ...buttonStyle,
            background: "#16a34a",
            opacity: !file || loading ? 0.6 : 1,
            cursor: !file || loading
              ? "not-allowed"
              : "pointer"
          }}
        >
          {loading ? "Please Wait..." : "Save Photo"}
        </button>

        <button
          type="button"
          onClick={handleToggleHistory}
          style={{
            ...buttonStyle,
            background: "#374151"
          }}
        >
          {showHistory
            ? "Hide Analysis History"
            : "View Analysis History"}
        </button>
      </div>

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
          <h3>Latest Gemini AI Analysis</h3>
          <AnalysisDetails analysis={result} />
        </div>
      )}

      {showHistory && (
        <div
          style={{
            textAlign: "left",
            marginTop: 30,
            padding: 20,
            borderRadius: 12,
            background: "#1f2937",
            color: "#ffffff"
          }}
        >
          <h3>Eye Analysis History</h3>

          <p>
            Review your previously saved eye analyses.
          </p>

          <button
            type="button"
            onClick={loadHistory}
            disabled={historyLoading}
            style={{
              ...buttonStyle,
              marginTop: 5,
              opacity: historyLoading ? 0.6 : 1
            }}
          >
            {historyLoading
              ? "Loading..."
              : "Refresh History"}
          </button>

          {historyError && (
            <p role="alert" style={{ color: "#fca5a5" }}>
              {historyError}
            </p>
          )}

          {!historyLoading &&
            !historyError &&
            history.length === 0 && (
              <p>
                No saved analyses yet.
                Your successful eye analyses will appear here.
              </p>
            )}

          {history.map((item) => (
            <article
              key={item.id}
              style={{
                background: "#f3f4f6",
                color: "#111827",
                padding: 20,
                marginTop: 20,
                borderRadius: 10
              }}
            >
              <h4>
                Analysis #{item.id}
              </h4>

              <SavedEyePhoto
                api={api}
                analysisId={item.id}
              />

              <p>
                <strong>Date: </strong>
                {new Date(item.created_at).toLocaleString()}
              </p>

              {item.analysis ? (
                <AnalysisDetails analysis={item.analysis} />
              ) : (
                <p>
                  Photo saved successfully. No AI analysis performed.
                </p>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
