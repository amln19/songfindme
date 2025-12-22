import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router";
import { ArrowLeftIcon } from "lucide-react";
import toast from "react-hot-toast";
import NavBar from "../components/NavBar";
import { useAuth } from "../context/AuthContext";
import { apiEndpoints } from "../api";

const AddSongPage = () => {
  const [title, setTitle] = useState("");
  const [artist, setArtist] = useState("");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);

  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!user) {
      toast.error("Please login first");
      navigate("/login");
      return;
    }
    if (user.role !== "admin") {
      toast.error("Not Authorized: You must be an admin to view this page.");
      navigate("/");
    }
  }, [user, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!title.trim() || !artist.trim() || !file) {
      toast.error("All fields are required");
      return;
    }

    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", title.trim());
      formData.append("artist", artist.trim());

      const res = await fetch(apiEndpoints.addSong, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${user.token}`,
        },
        body: formData,
      });

      if (res.status === 401 || res.status === 403) {
        throw new Error("Permission denied");
      }

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Upload failed");
      }

      const data = await res.json();
      toast.success(`Song uploaded successfully! ${data.fingerprints} fingerprints generated.`);
      
      // Reset form
      setTitle("");
      setArtist("");
      setFile(null);
      
      navigate("/");
    } catch (err) {
      console.error(err);
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!user || user.role !== "admin") return null;

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
                Add a New Song
              </h2>

              <form className="flex flex-col gap-5" onSubmit={handleSubmit}>
                <div className="form-control flex flex-col gap-1">
                  <label className="label">
                    <span className="label-text">Song Title</span>
                  </label>
                  <input
                    type="text"
                    className="input input-bordered"
                    placeholder="Enter song title"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                  />
                </div>

                <div className="form-control flex flex-col gap-1">
                  <label className="label">
                    <span className="label-text">Artist Name</span>
                  </label>
                  <input
                    type="text"
                    className="input input-bordered"
                    placeholder="Enter artist name"
                    value={artist}
                    onChange={(e) => setArtist(e.target.value)}
                  />
                </div>

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
                  <label className="label">
                    <span className="label-text-alt">Supported: MP3, WAV, M4A, FLAC, OGG</span>
                  </label>
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
                        Processing...
                      </span>
                    ) : (
                      "Add Song"
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AddSongPage;