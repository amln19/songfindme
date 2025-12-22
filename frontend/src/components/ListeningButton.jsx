import { useState, useRef, useEffect } from "react";
import { Mic, X, Music2 } from "lucide-react";
import toast from "react-hot-toast";
import { useAuth } from "../context/AuthContext";
import { apiEndpoints } from "../api";

const ListeningButton = () => {
  const [isListening, setIsListening] = useState(false);
  const [status, setStatus] = useState("idle");
  const [result, setResult] = useState(null);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const streamRef = useRef(null);
  const timerRef = useRef(null);
  const isMountedRef = useRef(true);

  const { user } = useAuth();

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      cleanup();
    };
  }, []);

  const identifyBlob = async (blob) => {
    const formData = new FormData();
    formData.append("file", blob, "recording.webm");

    const headers = {};
    if (user && user.token) {
      headers["Authorization"] = `Bearer ${user.token}`;
    }

    try {
      const res = await fetch(apiEndpoints.identify, {
        method: "POST",
        headers: headers,
        body: formData,
      });

      if (!res.ok) return null;
      const data = await res.json();

      if (!data.match_song_id) return null;

      return data;
    } catch (err) {
      console.error(err);
      return null;
    }
  };

  const startListening = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.start();
      setIsListening(true);
      setStatus("listening");
      setResult(null);

      // 5-second check
      timerRef.current = setTimeout(() => {
        if (!isMountedRef.current) return;
        performIntermediateCheck("continuing", () => {
          // 10-second check
          timerRef.current = setTimeout(() => {
            if (!isMountedRef.current) return;
            performIntermediateCheck("last_try", () => {
              // 15-second final check
              timerRef.current = setTimeout(() => {
                if (!isMountedRef.current) return;
                stopAndFinalCheck();
              }, 5000);
            });
          }, 5000);
        });
      }, 5000);
    } catch (err) {
      console.error(err);
      toast.error("Microphone access denied");
      setStatus("idle");
    }
  };

  const performIntermediateCheck = (nextStatus, onFailNextStep) => {
    if (
      !mediaRecorderRef.current ||
      mediaRecorderRef.current.state !== "recording"
    )
      return;

    mediaRecorderRef.current.requestData();

    setTimeout(async () => {
      if (!isMountedRef.current) return;
      
      console.log(`Performing intermediate check... Next status if fail: ${nextStatus}`);
      const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });

      const match = await identifyBlob(blob);

      if (match) {
        handleSuccess(match);
      } else {
        setStatus(nextStatus);
        if (onFailNextStep) onFailNextStep();
      }
    }, 200); // Increased delay to ensure chunk is ready
  };

  const stopAndFinalCheck = () => {
    if (!mediaRecorderRef.current) return;

    mediaRecorderRef.current.stop();

    mediaRecorderRef.current.onstop = async () => {
      if (!isMountedRef.current) return;
      
      const blobFinal = new Blob(audioChunksRef.current, {
        type: "audio/webm",
      });
      console.log("Attempting final 15s check...");

      const match = await identifyBlob(blobFinal);

      if (match) {
        handleSuccess(match);
      } else {
        handleFailure();
      }

      cleanup();
    };
  };

  const handleSuccess = (data) => {
    if (!isMountedRef.current) return;
    setResult(data);
    setStatus("success");
    cleanup();
    toast.success("Song identified!", { icon: "🎵" });
  };

  const handleFailure = () => {
    if (!isMountedRef.current) return;
    setStatus("failed");
    toast.error("No match found");
    cleanup();
  };

  const cancelListening = () => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state === "recording"
    ) {
      mediaRecorderRef.current.stop();
    }
    cleanup();
    setStatus("idle");
    setResult(null);
  };

  const cleanup = () => {
    setIsListening(false);
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  };

  if (status === "success" && result) {
    return (
      <div className="card w-100 bg-base-200 border border-info drop-shadow-[0_0_30px_oklch(74%_0.16_232.661)] transition-transform duration-300 hover:scale-105 animate-in fade-in zoom-in">
        <div className="card-body items-center text-center">
          <div className="size-20 bg-success/20 rounded-full flex items-center justify-center mb-2">
            <Music2 className="size-10 text-success" />
          </div>
          <h2 className="card-title text-2xl">{result.title}</h2>
          <p className="text-lg opacity-80">{result.artist}</p>
          <div className="card-actions mt-4">
            <button
              onClick={() => setStatus("idle")}
              className="btn btn-neutral"
            >
              Identify Another Song
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative group mb-8">
        {isListening && (
          <>
            <div className="absolute inset-0 rounded-full bg-neutral/50 animate-ping"></div>
            <div className="absolute -inset-4 rounded-full bg-neutral/40 animate-pulse"></div>
          </>
        )}

        <button
          onClick={isListening ? cancelListening : startListening}
          className="btn btn-circle btn-lg size-70 relative z-10 border-2 border-base-100 drop-shadow-[0_0_30px_oklch(74%_0.16_232.661)] transition-transform duration-300 hover:scale-105"
          aria-label={isListening ? "Cancel listening" : "Start listening"}
        >
          {isListening ? (
            <X className="size-14 text-error" />
          ) : (
            <div className="flex flex-col items-center gap-1 text-info">
              <Mic className="size-14" />
              <span className="text-sm font-bold uppercase tracking-widest">
                Tap
              </span>
            </div>
          )}
        </button>
      </div>

      <div className="h-10 flex items-center justify-center">
        {status === "idle" && (
          <p className="text-base-content/70 text-lg">
            Tap to Start Identifying
          </p>
        )}

        {status === "listening" && (
          <span className="loading loading-dots loading-lg text-secondary"></span>
        )}

        {status === "continuing" && (
          <div className="flex flex-col items-center">
            <span className="loading loading-dots loading-md text-info mb-1"></span>
            <span className="text-lg font-medium text-info animate-pulse">
              Continuing to analyze...
            </span>
          </div>
        )}

        {status === "last_try" && (
          <div className="flex flex-col items-center">
            <span className="loading loading-dots loading-md text-warning mb-1"></span>
            <span className="text-lg font-medium text-warning animate-pulse">
              One last try...
            </span>
          </div>
        )}

        {status === "failed" && (
          <div className="flex items-center gap-2 text-error font-medium animate-bounce">
            <X className="size-5" />
            <span>No match found. Try again.</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default ListeningButton;