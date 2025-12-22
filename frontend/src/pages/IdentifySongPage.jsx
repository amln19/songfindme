import { useState } from "react";
import { Link } from "react-router";
import { ArrowLeftIcon } from "lucide-react";
import toast from "react-hot-toast";
import NavBar from "../components/NavBar.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { apiEndpoints } from "../api.js";

const IdentifySongPage = () => {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const { user } = useAuth();

  const handleIdentify = async (e) => {
    e.preventDefault();

    if (!file) {
      toast.error("Please upload an audio file");
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const headers = {};
      if (user && user.token) {
        headers["Authorization"] = `Bearer ${user.token}`;
      }

      const res = await fetch(apiEndpoints.identify, {
        method: "POST",
        headers: headers,
        body: formData,
      });
      
      if (!res.ok) {
        throw new Error("Identification failed");
      }

      const data = await res.json();

      if (!data.match_song_id) {
        toast.error(data.message || "No match found");
        setResult(null);
      } else {
        setResult(data);
        toast.success("Song identified!");
      }

    } catch (err) {
      console.error(err);
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-base-300">
      <NavBar />

      <div className="container mx-auto px-4 py-10">
        <div className="max-w-xl mx-auto">
          <Link to="/" className="btn btn-ghost mb-6">
            <ArrowLeftIcon className="size-5" />
            Back Home
          </Link>

          <div className="card bg-base-200 border border-base-300 shadow-lg p-5">
            <div className="card-body">
              <h2 className="text-2xl font-semibold mb-6 text-center">
                Identify a Song
              </h2>

              <form className="flex flex-col gap-5" onSubmit={handleIdentify}>
                <div className="form-control flex flex-col gap-1">
                  <label className="label">
                    <span className="label-text">Upload Audio File</span>
                  </label>
                  <input
                    type="file"
                    accept="audio/*"
                    className="file-input file-input-bordered w-full"
                    onChange={(e) => setFile(e.target.files[0])}
                  />
                </div>

                <div className="flex justify-end pt-3">
                  <button
                    type="submit"
                    className="btn btn-primary px-8"
                    disabled={loading}
                  >
                    {loading ? (
                      <span className="flex items-center gap-2">
                        <span className="loading loading-spinner loading-sm"></span>
                        Identifying...
                      </span>
                    ) : (
                      "Identify Song"
                    )}
                  </button>
                </div>
              </form>

              {result && (
                <div className="mt-6 p-4 bg-base-100 rounded-lg border border-base-300 shadow">
                  <h3 className="text-lg font-semibold mb-3">Result</h3>
                  <p>
                    <span className="font-medium">Title:</span> {result.title}
                  </p>
                  <p>
                    <span className="font-medium">Artist:</span> {result.artist}
                  </p>
                  <p className="text-sm opacity-70 mt-2">
                    Matched {result.matched_hashes_count} fingerprints
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default IdentifySongPage;