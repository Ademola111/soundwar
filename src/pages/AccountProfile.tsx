import { useAuth } from "@/contexts/AuthContext";
import ArtistProfile from "@/pages/ArtistProfile";
import Profile from "@/pages/Profile";

const AccountProfile = () => {
  const { user } = useAuth();

  if (user?.roles.includes("admin")) {
    return <Profile />;
  }

  if (user?.roles.includes("artist") && user.artist_profile) {
    return <ArtistProfile />;
  }

  return <Profile />;
};

export default AccountProfile;
