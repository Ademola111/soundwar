import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Award, CalendarDays, Camera, LayoutDashboard, LogOut, Music2, Save, Settings, Vote, X } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/contexts/AuthContext";
import { API_ENDPOINTS, getAuthHeaders } from "@/config/api";
import { useToast } from "@/hooks/use-toast";

type VoteHistoryItem = {
  id: number;
  song_id: number;
  song_title: string | null;
  artist_id: number | null;
  artist_name: string | null;
  contest_id: number;
  contest_title: string | null;
  created_at: string | null;
};

type ArtistSong = {
  id: number;
  title: string;
  status: string;
  vote_count: number;
  created_at: string | null;
};

const Profile = () => {
  const navigate = useNavigate();
  const { user, token, isLoading, logout, refreshUser } = useAuth();
  const { toast } = useToast();
  const [voteHistory, setVoteHistory] = useState<VoteHistoryItem[]>([]);
  const [artistSongs, setArtistSongs] = useState<ArtistSong[]>([]);
  const [isLoadingActivity, setIsLoadingActivity] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showEditor, setShowEditor] = useState(false);
  const [profileImageFile, setProfileImageFile] = useState<File | null>(null);
  const [profileForm, setProfileForm] = useState({
    name: "",
    username: "",
    stage_name: "",
    genre: "",
    bio: "",
    profile_image: "",
  });

  const isAdmin = Boolean(user?.roles.includes("admin"));
  const isArtist = !isAdmin && (Boolean(user?.artist_profile) || Boolean(user?.roles.includes("artist")));
  const artist = user?.artist_profile;
  const profileImage = isArtist
    ? artist?.profile_image || user?.profile_image || ""
    : user?.profile_image || "";

  useEffect(() => {
    if (!user) return;
    setProfileForm({
      name: user.name || "",
      username: user.username || "",
      stage_name: artist?.stage_name || "",
      genre: artist?.genre || "",
      bio: artist?.bio || "",
      profile_image: profileImage,
    });
  }, [user, artist, profileImage]);

  useEffect(() => {
    if (!token || isAdmin) {
      setVoteHistory([]);
      return;
    }
    let active = true;

    const loadActivity = async () => {
      setIsLoadingActivity(true);
      const requests = [
        fetch(API_ENDPOINTS.VOTES.MY_HISTORY, { headers: getAuthHeaders(token) }),
        ...(isArtist
          ? [fetch(API_ENDPOINTS.SONGS.MY_SUBMISSIONS, { headers: getAuthHeaders(token) })]
          : []),
      ];

      try {
        const responses = await Promise.all(requests);
        if (!active) return;

        if (responses[0].ok) {
          const data = await responses[0].json();
          setVoteHistory(data.votes || []);
        }
        if (isArtist && responses[1]?.ok) {
          const data = await responses[1].json();
          setArtistSongs(data.songs || []);
        }
      } catch (error) {
        console.error("Failed to load profile activity", error);
      } finally {
        if (active) setIsLoadingActivity(false);
      }
    };

    loadActivity();
    return () => {
      active = false;
    };
  }, [token, isArtist, isAdmin]);

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const handleSaveProfile = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token || !user) return;

    const cleanedName = profileForm.name.trim();
    const cleanedUsername = profileForm.username.trim();
    if (!cleanedName || cleanedName.length > 100) {
      toast({ title: "Invalid name", description: "Enter a name of 1 to 100 characters.", variant: "destructive" });
      return;
    }
    if (!/^[a-zA-Z0-9_]{3,30}$/.test(cleanedUsername)) {
      toast({ title: "Invalid username", description: "Use 3 to 30 letters, numbers, or underscores.", variant: "destructive" });
      return;
    }
    if (isArtist && !artist && !profileForm.stage_name.trim()) {
      toast({ title: "Stage name required", description: "Enter an artist stage name to create your artist profile.", variant: "destructive" });
      return;
    }

    setIsSaving(true);
    try {
      const userForm = new FormData();
      userForm.append("name", cleanedName);
      userForm.append("username", cleanedUsername);
      if (!isArtist) {
        if (profileImageFile) userForm.append("profile_image", profileImageFile);
        else userForm.append("profile_image", profileForm.profile_image);
      }

      const userResponse = await fetch(API_ENDPOINTS.AUTH.PROFILE, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}` },
        body: userForm,
      });
      const userData = await userResponse.json().catch(() => ({}));
      if (!userResponse.ok) {
        throw new Error(userData.error || "Unable to update your account details.");
      }

      if (isArtist) {
        const artistDetails = {
          stage_name: profileForm.stage_name.trim(),
          genre: profileForm.genre.trim(),
          bio: profileForm.bio.trim(),
          profile_image: profileForm.profile_image.trim(),
        };
        const artistResponse = await fetch(
          artist ? API_ENDPOINTS.ARTISTS.PROFILE : API_ENDPOINTS.ARTISTS.CREATE,
          {
            method: artist ? "PUT" : "POST",
            headers: getAuthHeaders(token),
            body: JSON.stringify(artist ? artistDetails : artistDetails),
          },
        );
        const artistData = await artistResponse.json().catch(() => ({}));
        if (!artistResponse.ok) {
          throw new Error(artistData.error || "Unable to update the artist profile.");
        }

        if (profileImageFile) {
          const imageForm = new FormData();
          imageForm.append("profile_image", profileImageFile);
          const imageResponse = await fetch(API_ENDPOINTS.ARTISTS.PROFILE_IMAGE, {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` },
            body: imageForm,
          });
          const imageData = await imageResponse.json().catch(() => ({}));
          if (!imageResponse.ok) {
            throw new Error(imageData.error || "Unable to upload the artist photo.");
          }
        }
      }

      await refreshUser();
      setProfileImageFile(null);
      setShowEditor(false);
      toast({ title: "Profile saved", description: "Your profile changes have been saved." });
    } catch (error) {
      toast({
        title: "Could not save profile",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-muted-foreground">Loading profile...</p>
      </div>
    );
  }

  if (!user || !token) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <main className="container mx-auto px-4 pt-32 pb-20">
          <Card className="mx-auto max-w-lg">
            <CardHeader><CardTitle>Sign in to view your profile</CardTitle></CardHeader>
            <CardContent><Button onClick={() => navigate("/login")}>Go to sign in</Button></CardContent>
          </Card>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="container mx-auto max-w-5xl px-4 pb-16 pt-24">
        <motion.section initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
          <Card className="mb-6 border-border/60">
            <CardContent className="flex flex-col gap-5 p-6 sm:flex-row sm:items-center">
              <Avatar className="h-20 w-20 border-2 border-primary">
                <AvatarImage src={profileImage} alt={isArtist ? artist?.stage_name : user.name || user.username} />
                <AvatarFallback>{(isArtist ? artist?.stage_name?.[0] : user.name?.[0] || user.username[0])?.toUpperCase() || "U"}</AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1">
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <h1 className="text-2xl font-semibold">{isArtist ? artist?.stage_name || "Artist profile" : user.name || user.username}</h1>
                  <Badge variant={isArtist ? "default" : "secondary"}>{isAdmin ? "Admin" : isArtist ? "Artist" : "Voter"}</Badge>
                </div>
                <p className="text-sm text-muted-foreground">@{user.username} · {user.email}</p>
                {isArtist && artist?.genre && <p className="mt-1 text-sm text-muted-foreground">{artist.genre}</p>}
                <p className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
                  <CalendarDays className="h-3.5 w-3.5" /> Joined {user.created_at ? new Date(user.created_at).toLocaleDateString() : "recently"}
                </p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setShowEditor((open) => !open)}>
                  {showEditor ? <X className="mr-2 h-4 w-4" /> : <Settings className="mr-2 h-4 w-4" />}
                  {showEditor ? "Close editor" : "Edit profile"}
                </Button>
                {isAdmin && (
                  <Button variant="default" onClick={() => navigate("/admin")}>
                    <LayoutDashboard className="mr-2 h-4 w-4" />Dashboard
                  </Button>
                )}
                <Button variant="ghost" size="icon" aria-label="Sign out" onClick={handleLogout}>
                  <LogOut className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.section>

        {showEditor && (
          <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
            <Card className="mb-6">
              <CardHeader><CardTitle>Edit profile</CardTitle></CardHeader>
              <CardContent>
                <form onSubmit={handleSaveProfile} className="grid gap-4 md:grid-cols-2">
                  <label className="space-y-2 text-sm">
                    <span className="text-muted-foreground">Full name</span>
                    <Input value={profileForm.name} onChange={(event) => setProfileForm((form) => ({ ...form, name: event.target.value }))} maxLength={100} required />
                  </label>
                  <label className="space-y-2 text-sm">
                    <span className="text-muted-foreground">Username</span>
                    <Input value={profileForm.username} onChange={(event) => setProfileForm((form) => ({ ...form, username: event.target.value }))} minLength={3} maxLength={30} required />
                  </label>
                  {isArtist && (
                    <>
                      <label className="space-y-2 text-sm">
                        <span className="text-muted-foreground">Artist stage name</span>
                        <Input value={profileForm.stage_name} onChange={(event) => setProfileForm((form) => ({ ...form, stage_name: event.target.value }))} maxLength={100} required />
                      </label>
                      <label className="space-y-2 text-sm">
                        <span className="text-muted-foreground">Genre</span>
                        <Input value={profileForm.genre} onChange={(event) => setProfileForm((form) => ({ ...form, genre: event.target.value }))} maxLength={50} />
                      </label>
                      <label className="space-y-2 text-sm md:col-span-2">
                        <span className="text-muted-foreground">Artist bio</span>
                        <textarea value={profileForm.bio} onChange={(event) => setProfileForm((form) => ({ ...form, bio: event.target.value }))} maxLength={1000} rows={4} className="w-full resize-y rounded-md border border-input bg-background px-3 py-2 text-sm" />
                      </label>
                    </>
                  )}
                  <label className="space-y-2 text-sm md:col-span-2">
                    <span className="text-muted-foreground">Profile photo URL (optional)</span>
                    <Input type="url" value={profileForm.profile_image} onChange={(event) => setProfileForm((form) => ({ ...form, profile_image: event.target.value }))} placeholder="https://example.com/photo.jpg" />
                  </label>
                  <label className="flex cursor-pointer items-center gap-3 rounded-md border border-dashed border-border p-4 text-sm md:col-span-2">
                    <Camera className="h-5 w-5 text-muted-foreground" />
                    <span className="min-w-0 flex-1">{profileImageFile ? profileImageFile.name : "Upload a JPG, PNG, or WebP photo (max 5 MB)"}</span>
                    <input type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" onChange={(event) => setProfileImageFile(event.target.files?.[0] || null)} />
                  </label>
                  <div className="flex justify-end md:col-span-2">
                    <Button type="submit" disabled={isSaving}>
                      <Save className="mr-2 h-4 w-4" />{isSaving ? "Saving..." : "Save changes"}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </motion.section>
        )}

        {isArtist ? (
          <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2"><Music2 className="h-5 w-5" /> Artist profile</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                {artist ? (
                  <>
                    <div className="flex flex-wrap gap-2">
                      <Badge variant={artist.is_verified ? "default" : "secondary"}>{artist.is_verified ? "Verified" : "Verification pending"}</Badge>
                      <Badge variant={artist.is_paid && !artist.requires_season_payment ? "default" : "outline"}>
                        {artist.requires_season_payment ? "Season payment pending" : artist.is_paid ? "Paid" : "Payment pending"}
                      </Badge>
                    </div>
                    <p className="text-sm leading-6 text-muted-foreground">{artist.bio || "Add a short bio using Edit profile."}</p>
                    {artist.can_participate === false && (
                      <p className="text-sm text-destructive">Past-winner cooldown: {artist.months_until_eligible || 0} months remaining.</p>
                    )}
                  </>
                ) : (
                  <div className="space-y-3">
                    <p className="text-sm text-muted-foreground">This artist account has no profile yet. Add a stage name and save using Edit profile to create it.</p>
                    <Button variant="outline" onClick={() => setShowEditor(true)}>Create artist profile</Button>
                  </div>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>My submissions</CardTitle>
                <Button variant="outline" size="sm" onClick={() => navigate("/submit")}>Submit a song</Button>
              </CardHeader>
              <CardContent>
                {isLoadingActivity ? <p className="text-sm text-muted-foreground">Loading submissions...</p> : artistSongs.length ? (
                  <div className="divide-y divide-border">
                    {artistSongs.map((song) => (
                      <div key={song.id} className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                        <div>
                          <p className="font-medium">{song.title}</p>
                          <p className="text-xs text-muted-foreground">{song.created_at ? new Date(song.created_at).toLocaleDateString() : "Date unavailable"}</p>
                        </div>
                        <div className="flex items-center gap-3">
                          <Badge variant={song.status === "approved" ? "default" : "secondary"}>{song.status}</Badge>
                          <span className="text-sm text-muted-foreground">{song.vote_count} votes</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : <p className="text-sm text-muted-foreground">No song submissions yet.</p>}
              </CardContent>
            </Card>
          </section>
        ) : isAdmin ? (
          <section>
            <Card className="max-w-2xl">
              <CardHeader><CardTitle className="flex items-center gap-2"><LayoutDashboard className="h-5 w-5" /> Administrator access</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">Your account has administrator access. Open the dashboard to manage users, songs, contests, and payments.</p>
                <Button onClick={() => navigate("/admin")}>
                  <LayoutDashboard className="mr-2 h-4 w-4" />Open admin dashboard
                </Button>
              </CardContent>
            </Card>
          </section>
        ) : (
          <section className="grid gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
            <Card>
              <CardHeader><CardTitle>Voting activity</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center gap-3"><Vote className="h-5 w-5 text-primary" /><span><strong>{voteHistory.length}</strong> votes cast</span></div>
                <div className="flex items-center gap-3"><Award className="h-5 w-5 text-accent" /><span><strong>{new Set(voteHistory.map((vote) => vote.contest_id)).size}</strong> seasons participated</span></div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Artists you voted for</CardTitle></CardHeader>
              <CardContent>
                {isLoadingActivity ? <p className="text-sm text-muted-foreground">Loading vote history...</p> : voteHistory.length ? (
                  <div className="divide-y divide-border">
                    {voteHistory.map((vote) => (
                      <div key={vote.id} className="grid gap-1 py-3 first:pt-0 last:pb-0 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)_auto] sm:items-center sm:gap-4">
                        <div className="min-w-0">
                          <p className="truncate font-medium">{vote.artist_name || "Artist unavailable"}</p>
                          <p className="truncate text-sm text-muted-foreground">{vote.song_title || "Song unavailable"}</p>
                        </div>
                        <p className="text-sm text-muted-foreground">{vote.contest_title || `Season ${vote.contest_id}`}</p>
                        <p className="text-xs text-muted-foreground">{vote.created_at ? new Date(vote.created_at).toLocaleDateString() : "Date unavailable"}</p>
                      </div>
                    ))}
                  </div>
                ) : <p className="text-sm text-muted-foreground">No votes have been recorded for this account yet.</p>}
              </CardContent>
            </Card>
          </section>
        )}
      </main>
      <Footer />
    </div>
  );
};

export default Profile;
