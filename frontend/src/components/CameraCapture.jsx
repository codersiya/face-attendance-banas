import { useEffect, useRef, useState } from "react";

/**
 * Reusable camera capture tile with:
 *  - Live guide overlay (oval + directional arrow) matching the requested pose
 *  - Mirrored preview for the front camera (natural "selfie" feel) - the
 *    mirroring is CSS-only on the <video>, so the actual captured frame
 *    (drawn from the video element onto <canvas>) is NOT mirrored, which
 *    keeps left/right pose detection on the backend consistent.
 *  - Flip button only shown when the device actually has more than one
 *    camera (checked via enumerateDevices).
 *
 * poseKey: "front" | "left" | "right" - purely for showing the right guide.
 * validationStatus: "idle" | "checking" | "valid" | "invalid"
 */
export default function CameraCapture({
  label,
  poseKey,
  onCapture,
  capturedPreviewUrl,
  validationStatus = "idle",
  validationMessage = "",
}) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  const [facingMode, setFacingMode] = useState("user");
  const [error, setError] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [hasMultipleCameras, setHasMultipleCameras] = useState(false);

  const stopCurrentStream = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  };

  // Detect whether this device even has a second camera - hides the Flip
  // button on plain webcams instead of showing a button that does nothing.
  useEffect(() => {
    navigator.mediaDevices
      ?.enumerateDevices()
      .then((devices) => {
        const cams = devices.filter((d) => d.kind === "videoinput");
        setHasMultipleCameras(cams.length > 1);
      })
      .catch(() => setHasMultipleCameras(false));
  }, []);

  useEffect(() => {
    if (capturedPreviewUrl) return undefined;

    let cancelled = false;

    const start = async () => {
      setError("");
      setIsStreaming(false);
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode, width: { ideal: 720 }, height: { ideal: 720 } },
          audio: false,
        });

        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }

        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          try {
            await videoRef.current.play();
          } catch (playErr) {
            if (playErr.name !== "AbortError") throw playErr;
          }
        }

        if (!cancelled) setIsStreaming(true);
      } catch (err) {
        if (!cancelled) {
          setError(
            err.name === "NotAllowedError"
              ? "Camera permission denied. Please allow camera access."
              : `Could not access camera: ${err.message}`
          );
        }
      }
    };

    start();

    return () => {
      cancelled = true;
      stopCurrentStream();
      setIsStreaming(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [facingMode, capturedPreviewUrl]);

  const handleCapture = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    // Draws directly from the video element - NOT mirrored, regardless of
    // the CSS mirroring applied to the preview below.
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        if (blob) onCapture(blob);
      },
      "image/jpeg",
      0.92
    );
    stopCurrentStream();
  };

  const handleRetake = () => {
    onCapture(null);
  };

  const isFrontCamera = facingMode === "user";

  return (
    <div className="camera-tile">
      <div className="camera-tile__label">{label}</div>

      <div className="camera-tile__frame">
        {capturedPreviewUrl ? (
          <img src={capturedPreviewUrl} alt={`${label} capture`} className="camera-tile__media" />
        ) : (
          <>
            <video
              ref={videoRef}
              muted
              playsInline
              className={`camera-tile__media ${isFrontCamera ? "camera-tile__media--mirrored" : ""}`}
            />
            {isStreaming && (
              <div className={`camera-tile__guide camera-tile__guide--${poseKey}`}>
                <div className="camera-tile__oval" />
                {poseKey !== "front" && (
                  <div className={`camera-tile__arrow camera-tile__arrow--${poseKey}`}>
                    {poseKey === "left" ? "⟲" : "⟳"}
                  </div>
                )}
              </div>
            )}
          </>
        )}
        <canvas ref={canvasRef} style={{ display: "none" }} />

        {error && <div className="camera-tile__error">{error}</div>}

        {validationStatus === "checking" && (
          <div className="camera-tile__status">Checking photo…</div>
        )}
      </div>

      {validationStatus === "invalid" && (
        <div className="camera-tile__validation camera-tile__validation--bad">
          {validationMessage || "That photo didn't work — please retake it."}
        </div>
      )}
      {validationStatus === "valid" && (
        <div className="camera-tile__validation camera-tile__validation--good">
          ✓ {validationMessage || "Looks good"}
        </div>
      )}

      <div className="camera-tile__actions">
        {capturedPreviewUrl ? (
          <button type="button" className="btn btn--ghost" onClick={handleRetake}>
            Retake
          </button>
        ) : (
          <>
            <button
              type="button"
              className="btn btn--primary"
              onClick={handleCapture}
              disabled={!isStreaming}
            >
              Capture
            </button>
            {hasMultipleCameras && (
              <button
                type="button"
                className="btn btn--ghost"
                onClick={() => setFacingMode((m) => (m === "user" ? "environment" : "user"))}
                title="Switch camera (front/back)"
              >
                Flip
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}