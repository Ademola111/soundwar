import { motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Upload, Music, FileAudio, Check, AlertCircle, Image, X, Clock } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/contexts/AuthContext";
import { useSubmitEligibility } from "@/hooks/useSubmitEligibility";
import { API_ENDPOINTS, APP_CONFIG, getAuthHeaders, getMultipartHeaders, sanitizeInput } from "@/config/api";

const Submit = () => {
  const { user, token, isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const { canSubmitSong, isChecking: isCheckingEligibility, reason: eligibilityReason } = useSubmitEligibility();
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [coverFile, setCoverFile] = useState<File | null>(null);
  const [coverPreview, setCoverPreview] = useState<string | null>(null);
  const [duration, setDuration] = useState<number | null>(null);
  const [isReadingDuration, setIsReadingDuration] = useState(false);
  const durationRequestId = useRef(0);
  const durationObjectUrl = useRef<string | null>(null);
  const [formData, setFormData] = useState({
    title: "",
    description: "",
  });
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const artistProfile = user?.artist_profile;
  const isArtist = Boolean(artistProfile);
  const isPaidArtist = Boolean(artistProfile?.is_paid);

  useEffect(() => {
    return () => {
      if (coverPreview) URL.revokeObjectURL(coverPreview);
    };
  }, [coverPreview]);

  useEffect(() => () => {
    if (durationObjectUrl.current) URL.revokeObjectURL(durationObjectUrl.current);
  }, []);

  useEffect(() => {
    if (isAuthLoading || isCheckingEligibility) return;
    if (!isAuthenticated) {
      navigate("/login", { replace: true });
      return;
    }
    if (canSubmitSong) return;

    const redirectPath = eligibilityReason === "unpaid"
      ? "/payment"
      : eligibilityReason === "not-artist" || eligibilityReason === "ineligible"
        ? "/artists"
        : eligibilityReason === "already-submitted"
          ? "/profile"
          : eligibilityReason === "outside-submission"
            ? "/leaderboard"
            : "/";
    navigate(redirectPath, { replace: true });
  }, [isAuthLoading, isCheckingEligibility, isAuthenticated, canSubmitSong, eligibilityReason, navigate]);

  const selectAudioFile = (selectedFile: File) => {
    const isMp3 = selectedFile.type === "audio/mpeg" || selectedFile.type === "audio/mp3" || selectedFile.name.toLowerCase().endsWith(".mp3");
    if (!isMp3) {
      setError("Please choose an MP3 file.");
      return;
    }
    if (selectedFile.size > APP_CONFIG.MAX_SONG_SIZE_MB * 1024 * 1024) {
      setError(`The MP3 file must be ${APP_CONFIG.MAX_SONG_SIZE_MB} MB or smaller.`);
      return;
    }
    const requestId = ++durationRequestId.current;
    if (durationObjectUrl.current) URL.revokeObjectURL(durationObjectUrl.current);
    setFile(selectedFile);
    setDuration(null);
    setIsReadingDuration(true);
    setError("");

    const audio = new Audio();
    const objectUrl = URL.createObjectURL(selectedFile);
    durationObjectUrl.current = objectUrl;
    audio.preload = "metadata";
    audio.onloadedmetadata = () => {
      URL.revokeObjectURL(objectUrl);
      if (requestId !== durationRequestId.current) return;
      durationObjectUrl.current = null;
      if (Number.isFinite(audio.duration) && audio.duration > 0) {
        setDuration(Math.round(audio.duration));
        setIsReadingDuration(false);
      } else {
        setIsReadingDuration(false);
        setError("Could not read this MP3's duration. Please choose another file.");
      }
    };
    audio.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      if (requestId !== durationRequestId.current) return;
      durationObjectUrl.current = null;
      setIsReadingDuration(false);
      setError("Could not read this MP3's duration. Please choose another file.");
    };
    audio.src = objectUrl;
  };

  const selectCoverFile = (selectedFile: File) => {
    const allowedTypes = ["image/jpeg", "image/png", "image/webp"];
    if (!allowedTypes.includes(selectedFile.type)) {
      setError("Cover art must be a JPG, PNG, or WebP image.");
      return;
    }
    if (selectedFile.size > APP_CONFIG.MAX_COVER_SIZE_MB * 1024 * 1024) {
      setError(`Cover art must be ${APP_CONFIG.MAX_COVER_SIZE_MB} MB or smaller.`);
      return;
    }

    setCoverFile(selectedFile);
    setCoverPreview(URL.createObjectURL(selectedFile));
    setError("");
  };

  const formatDuration = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    return `${minutes}:${String(seconds % 60).padStart(2, "0")}`;
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) selectAudioFile(droppedFile);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) selectAudioFile(selectedFile);
    e.currentTarget.value = "";
  };

  const handlePayment = async () => {
    if (!token) {
      navigate("/login");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const txRef = `SW-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      const response = await fetch(API_ENDPOINTS.PAYMENTS.INITIALIZE, {
        method: "POST",
        headers: getAuthHeaders(token),
        body: JSON.stringify({
          tx_ref: txRef,
          amount: APP_CONFIG.ARTIST_REGISTRATION_FEE,
          currency: APP_CONFIG.CURRENCY,
          redirect_url: `${window.location.origin}/payment/success`,
          email: user?.email,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || data.message || "Could not initialize payment.");
      }

      if (data.payment_link) {
        window.location.href = data.payment_link;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start payment.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!isAuthenticated) {
      navigate("/login");
      return;
    }

    if (!isArtist) {
      setError("Only artists can submit songs.");
      return;
    }

    if (!isPaidArtist) {
      setError("Payment is required before submitting your song.");
      return;
    }

    if (!canSubmitSong) {
      setError("Song submissions are not available for this artist or contest right now.");
      return;
    }

    if (!file || !token) return;

    setIsLoading(true);
    setError("");
    try {
      const submission = new FormData();
      submission.append("title", sanitizeInput(formData.title));
      submission.append("audio_file", file);
      submission.append("duration", String(duration));
      if (coverFile) submission.append("cover_file", coverFile);

      const response = await fetch(`${API_ENDPOINTS.SONGS.BASE}/submit`, {
        method: "POST",
        headers: getMultipartHeaders(token),
        body: submission,
      });
      const data = await response.json() as { error?: string; message?: string };
      if (!response.ok) {
        throw new Error(data.error || data.message || "Could not submit your track.");
      }
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to submit your track.");
    } finally {
      setIsLoading(false);
    }
  };

  if (isAuthLoading || isCheckingEligibility || !isAuthenticated || !canSubmitSong) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center" role="status">
        <p className="text-muted-foreground">Checking song submission availability...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="pt-24 pb-20">
        <div className="container mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-2xl mx-auto"
          >
            {/* Header */}
            <div className="text-center mb-8">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/20 text-primary mb-6">
                <Upload className="w-4 h-4" />
                <span className="text-sm font-semibold">Submit Your Track</span>
              </div>
              <h1 className="font-display text-3xl md:text-4xl font-bold mb-4">
                Upload Your <span className="text-gradient-primary">Song</span>
              </h1>
              <p className="text-muted-foreground max-w-xl mx-auto">
                Submit your best track to compete in SoundWars. Only one submission per artist.
              </p>
            </div>

            {/* Submission Form */}
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* File Upload */}
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                className={`glass rounded-2xl p-8 border-2 border-dashed transition-all ${
                  isDragging
                    ? "border-primary bg-primary/10"
                    : file
                    ? "border-green-500/50 bg-green-500/5"
                    : "border-border hover:border-primary/50"
                }`}
              >
                <input
                  type="file"
                  accept="audio/mpeg"
                  onChange={handleFileChange}
                  className="hidden"
                  id="audio-upload"
                />
                
                <label
                  htmlFor="audio-upload"
                  className="flex flex-col items-center cursor-pointer"
                >
                  {file ? (
                    <>
                      <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mb-4">
                        <Check className="w-8 h-8 text-green-500" />
                      </div>
                      <h3 className="font-semibold text-lg mb-1">{file.name}</h3>
                      <p className="text-sm text-muted-foreground">
                        {(file.size / (1024 * 1024)).toFixed(2)} MB
                      </p>
                      <p className="text-sm text-muted-foreground mt-1 flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        {isReadingDuration
                          ? "Reading duration..."
                          : duration === null ? "Duration unavailable" : formatDuration(duration)}
                      </p>
                      <p className="text-sm text-primary mt-2">Click to change file</p>
                    </>
                  ) : (
                    <>
                      <div className="w-16 h-16 rounded-full bg-primary/20 flex items-center justify-center mb-4">
                        <FileAudio className="w-8 h-8 text-primary" />
                      </div>
                      <h3 className="font-semibold text-lg mb-1">
                        Drop your MP3 file here
                      </h3>
                      <p className="text-sm text-muted-foreground mb-4">
                        or click to browse from your device
                      </p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <AlertCircle className="w-4 h-4" />
                        Max file size: {APP_CONFIG.MAX_SONG_SIZE_MB}MB • MP3 format only
                      </div>
                    </>
                  )}
                </label>
              </div>

              <div className="glass rounded-2xl p-6">
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div>
                    <Label htmlFor="cover-upload" className="text-base font-semibold">Cover Art</Label>
                    <p className="text-sm text-muted-foreground mt-1">Optional JPG, PNG, or WebP image, up to {APP_CONFIG.MAX_COVER_SIZE_MB} MB.</p>
                  </div>
                  {coverFile && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      aria-label="Remove cover art"
                      onClick={() => {
                        setCoverFile(null);
                        setCoverPreview(null);
                      }}
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  )}
                </div>
                <input
                  id="cover-upload"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  className="sr-only"
                  onChange={(event) => {
                    const selectedFile = event.target.files?.[0];
                    if (selectedFile) selectCoverFile(selectedFile);
                    event.currentTarget.value = "";
                  }}
                />
                <label
                  htmlFor="cover-upload"
                  className="flex items-center gap-4 cursor-pointer rounded-lg border border-dashed border-border p-4 hover:border-primary/50 transition-colors"
                >
                  {coverPreview ? (
                    <img src={coverPreview} alt="Selected cover art preview" className="w-20 h-20 rounded-md object-cover" />
                  ) : (
                    <div className="w-20 h-20 rounded-md bg-primary/10 flex items-center justify-center">
                      <Image className="w-7 h-7 text-primary" />
                    </div>
                  )}
                  <span className="text-sm text-muted-foreground">
                    {coverFile ? `${coverFile.name} · Click to change` : "Choose cover art"}
                  </span>
                </label>
              </div>

              {/* Song Details */}
              <div className="glass rounded-2xl p-6 space-y-5">
                <div className="space-y-2">
                  <Label htmlFor="title">Song Title</Label>
                  <div className="relative">
                    <Music className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      id="title"
                      placeholder="Enter your song title"
                      className="pl-10"
                      value={formData.title}
                      onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                      required
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="description">Song Description</Label>
                  <Textarea
                    id="description"
                    placeholder="Tell us about your song... (optional)"
                    className="min-h-[100px] resize-none"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  />
                </div>
              </div>

              {/* Guidelines */}
              <div className="glass rounded-2xl p-6">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-primary" />
                  Submission Guidelines
                </h3>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                    You can only submit one song per competition
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                    The song must be your original work
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                    File must be in MP3 format, max {APP_CONFIG.MAX_SONG_SIZE_MB}MB
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                    Track duration is detected from the MP3; cover art is optional
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                    Submissions close when registration period ends
                  </li>
                </ul>
              </div>

              {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
              {submitted && (
                <p role="status" className="text-sm text-green-600">
                  Track submitted successfully. It is pending approval.
                </p>
              )}

              <Button
                type="submit"
                variant="hero"
                size="xl"
                className="w-full"
                disabled={!file || duration === null || isReadingDuration || !formData.title.trim() || isLoading || submitted}
              >
                {submitted ? <Check className="w-5 h-5" /> : <Upload className="w-5 h-5" />}
                {isLoading ? "Submitting..." : submitted ? "Track Submitted" : "Submit Track"}
              </Button>
            </form>
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
};

export default Submit;
