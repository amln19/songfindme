import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { ArrowLeftIcon } from "lucide-react";
import toast from "react-hot-toast";
import NavBar from "../components/NavBar";
import { useAuth } from "../context/AuthContext";
import { apiEndpoints } from "../api";

const HistoryPage = () => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!user) {
      navigate("/");
      return;
    }

    const fetchHistory = async () => {
      try {
        const res = await fetch(apiEndpoints.history, {
          headers: {
            Authorization: `Bearer ${user.token}`,
          },
        });

        if (!res.ok) {
          throw new Error(
            "Failed to fetch history. Please try logging out and signing back in"
          );
        }

        const data = await res.json();
        setHistory(data);
      } catch (err) {
        console.error(err);
        toast.error("Could not load history");
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [user, navigate]);

  return (
    <div className="min-h-screen bg-base-300">
      <NavBar />

      <div className="container mx-auto px-4 py-10">
        <div className="max-w-4xl mx-auto">
          <Link to="/" className="btn btn-ghost mb-6">
            <ArrowLeftIcon className="size-5" />
            Back Home
          </Link>

          <h2 className="text-3xl font-bold mb-6">
            Your Identification History
          </h2>

          <div className="card bg-base-100 shadow-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="table w-full">
                <thead>
                  <tr className="bg-base-200">
                    <th>#</th>
                    <th>Title</th>
                    <th>Artist</th>
                    <th>Date Identified</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr>
                      <td colSpan="4" className="text-center py-8">
                        <span className="loading loading-spinner loading-lg"></span>
                      </td>
                    </tr>
                  ) : history.length === 0 ? (
                    <tr>
                      <td
                        colSpan="4"
                        className="text-center py-8 text-gray-500"
                      >
                        No songs identified yet.
                      </td>
                    </tr>
                  ) : (
                    history.map((item, index) => (
                      <tr key={index} className="hover">
                        <th>{history.length - index}</th>
                        <td className="font-semibold text-lg">{item.title}</td>
                        <td>{item.artist}</td>
                        <td className="text-sm opacity-70">
                          {new Date(item.date).toLocaleString()}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HistoryPage;