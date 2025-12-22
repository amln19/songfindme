import NavBar from "../components/NavBar";
import ListeningButton from "../components/ListeningButton";

const HomePage = () => {
  return (
    <div className="min-h-screen flex flex-col">
      <NavBar />

      <div className="flex flex-1 flex-col items-center justify-center pb-5">
        <div className="mb-18 text-center space-y-4">
          <h1 className="text-5xl md:text-7xl font-black tracking-tight drop-shadow-[0_0_50px_oklch(90%_0.076_70.697)]">
            SongFindMe
          </h1>
          <p className="text-xl text-base-content/70 max-w-md mx-auto">
            Discover music around you. Instantly.
          </p>
        </div>

        {/* The Magic Button */}
        <ListeningButton />
      </div>
    </div>
  );
};

export default HomePage;