import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Check, ImagePlus, Loader2, Music2, Save, Upload, UserRound, X } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { API_ENDPOINTS, getAuthHeaders, getMultipartHeaders, sanitizeInput } from "@/config/api";

const ArtistProfile = () => {
  const navigate = useNavigate();
  const { user, token, isLoading: isAuthLoading, isAuthenticated, refreshUser } = useAuth();
  const { toast } = useToast();
  const artist = user?.artist_profile;
  const [stageName, setStageName] = useState("");
  const [genre, setGenre] = useState("");
  const [bio, setBio] = useState("");
  const [profileImage, setProfileImage] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isUploadingImage, setIsUploadingImage] = useState(false);
  const [error, setError] = useState("");
  const imageInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!isAuthLoading && !isAuthenticated) navigate("/login", { replace: true });
  }, [isAuthLoading, isAuthenticated, navigate]);

  useEffect(() => {
    if (!artist) return;
    setStageName(artist.stage_name || "");
    setGenre(artist.genre || "");
    setBio(artist.bio || "");
    setProfileImage(artist.profile_image || artist.avatar_url || "");
  }, [artist]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token) return;

    setError("");
    setIsSaving(true);
    try {
      const response = await fetch(API_ENDPOINTS.ARTISTS.PROFILE, {
        method: "PUT",
        headers: getAuthHeaders(token),
        body: JSON.stringify({
          stage_name: sanitizeInput(stageName),
          genre: sanitizeInput(genre),
          bio: sanitizeInput(bio),
          profile_image: profileImage.trim() || null,
        }),
      });
      const data = await response.json() as { error?: string; message?: string };
      if (!response.ok) throw new Error(data.error || data.message || "Could not update your profile.");

      await refreshUser();
      toast({ title: "Profile updated", description: "Your artist details have been saved." });
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Could not update your profile.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleProfileImageChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.currentTarget.value = "";
    if (!file || !token) return;

    const allowedTypes = ["image/jpeg", "image/png", "image/webp"];
    if (!allowedTypes.includes(file.type)) {
      setError("Choose a JPG, PNG, or WebP image.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError("Display pictures must be 5 MB or smaller.");
      return;
    }

    setError("");
    setIsUploadingImage(true);
    try {
      const upload = new FormData();
      upload.append("profile_image", file);
      const response = await fetch(API_ENDPOINTS.ARTISTS.PROFILE_IMAGE, {
        method: "POST",
        headers: getMultipartHeaders(token),
        body: upload,
      });
      const data = await response.json() as {
        error?: string;
        artist?: { profile_image?: string | null };
      };
      if (!response.ok) throw new Error(data.error || "Could not upload your display picture.");

      setProfileImage(data.artist?.profile_image || "");
      toast({ title: "Display picture updated", description: "Your new picture is now on your artist profile." });
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Could not upload your display picture.");
    } finally {
      setIsUploadingImage(false);
    }
  };

  if (isAuthLoading || !isAuthenticated) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center" role="status">
        <Loader2 className="w-5 h-5 animate-spin text-primary" />
        <span className="ml-2 text-muted-foreground">Loading profile...</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="container mx-auto px-4 pt-24 pb-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-3xl mx-auto"
        >
          <header className="mb-8">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-accent/20 text-accent mb-4">
              <UserRound className="w-4 h-4" />
              <span className="text-sm font-semibold">Artist Profile</span>
            </div>
            <h1 className="font-display text-3xl md:text-4xl font-bold">Your artist identity</h1>
            <p className="text-muted-foreground mt-2">Keep your public artist details current for listeners and voters.</p>
          </header>

          {!artist ? (
            <section className="glass rounded-2xl p-8 text-center">
              <Music2 className="w-10 h-10 mx-auto mb-4 text-primary" />
              <h2 className="text-xl font-semibold">No artist profile on this account</h2>
              <p className="text-muted-foreground mt-2 mb-5">This account is registered as a voter. Artist profile editing is available on accounts with an artist profile.</p>
              <Link to="/artists">
                <Button variant="outline">Browse competitors</Button>
              </Link>
            </section>
          ) : (
            <div className="grid gap-8 md:grid-cols-[240px_1fr]">
              <aside className="space-y-5">
                <div className="glass rounded-2xl p-6 flex flex-col items-center text-center">
                  <Avatar className="w-28 h-28 border-2 border-primary/50">
                    <AvatarImage src={profileImage || undefined} alt={stageName} />
                    <AvatarFallback className="bg-primary/15 text-primary text-3xl">
                      {(stageName || user?.username || "A").charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <h2 className="font-display text-xl font-bold mt-4">{stageName || "Your stage name"}</h2>
                  <p className="text-sm text-muted-foreground mt-1">{genre || "Genre not set"}</p>
                  <div className="mt-4 flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${artist.requires_season_payment ? "bg-yellow-500" : "bg-green-500"}`} />
                    <span className="text-xs text-muted-foreground">
                      {artist.requires_season_payment
                        ? "Current season payment pending"
                        : artist.is_returning_artist && artist.has_paid_for_current_contest
                          ? "Current season payment complete"
                          : artist.is_paid
                            ? "Registration paid"
                            : "Payment pending"}
                    </span>
                  </div>
                </div>
                <div className="px-1 text-sm text-muted-foreground space-y-1">
                  <p>Account: {user?.username}</p>
                  <p className="truncate">Email: {user?.email}</p>
                </div>
              </aside>

              <form onSubmit={handleSubmit} className="glass rounded-2xl p-6 md:p-8 space-y-6">
                <div className="flex items-center justify-between gap-4 border-b border-border pb-4">
                  <div>
                    <h2 className="font-semibold text-lg">Public profile details</h2>
                    <p className="text-sm text-muted-foreground">These details appear on your artist card.</p>
                  </div>
                  <Check className="w-5 h-5 text-accent shrink-0" />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="stage-name">Stage name</Label>
                  <Input id="stage-name" value={stageName} onChange={(event) => setStageName(event.target.value)} maxLength={100} required />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="genre">Genre</Label>
                  <Input id="genre" value={genre} onChange={(event) => setGenre(event.target.value)} placeholder="e.g. Afrobeats, R&B, Hip-hop" maxLength={50} />
                </div>

                <div className="space-y-3">
                  <Label>Display picture</Label>
                  <div className="flex flex-wrap items-center gap-4 rounded-lg border border-border p-4">
                    <Avatar className="w-16 h-16">
                      <AvatarImage src={profileImage || undefined} alt={stageName} />
                      <AvatarFallback className="bg-primary/15 text-primary">
                        {(stageName || user?.username || "A").charAt(0).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex flex-wrap items-center gap-2">
                      <input
                        ref={imageInputRef}
                        type="file"
                        accept="image/jpeg,image/png,image/webp"
                        className="sr-only"
                        onChange={handleProfileImageChange}
                      />
                      <Button type="button" variant="outline" onClick={() => imageInputRef.current?.click()} disabled={isUploadingImage}>
                        {isUploadingImage ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Upload className="w-4 h-4 mr-2" />}
                        {isUploadingImage ? "Uploading..." : "Choose picture"}
                      </Button>
                      {profileImage && (
                        <Button type="button" variant="ghost" onClick={() => setProfileImage("")} disabled={isUploadingImage}>
                          <X className="w-4 h-4 mr-2" />Remove
                        </Button>
                      )}
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground flex items-center gap-1">
                    <ImagePlus className="w-3.5 h-3.5" /> JPG, PNG, or WebP, up to 5 MB. Upload saves immediately.
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="bio">Artist bio</Label>
                  <Textarea id="bio" value={bio} onChange={(event) => setBio(event.target.value)} placeholder="Tell listeners about your sound and story..." className="min-h-36 resize-y" maxLength={1000} />
                  <p className="text-xs text-muted-foreground text-right">{bio.length}/1000</p>
                </div>

                {error && <p role="alert" className="text-sm text-destructive">{error}</p>}

                <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-3 border-t border-border pt-5">
                  <Button type="submit" variant="hero" disabled={isSaving || !stageName.trim()}>
                    {isSaving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                    {isSaving ? "Saving..." : "Save profile"}
                  </Button>
                </div>
              </form>
            </div>
          )}
        </motion.div>
      </main>
      <Footer />
    </div>
  );
};

export default ArtistProfile;
