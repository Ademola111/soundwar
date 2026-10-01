import { motion } from "framer-motion";
import { Play, Pause, Heart, Trophy, Check, Lock, Music2, Clock } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { useVoting } from "@/hooks/useVoting";
import { useToast } from "@/hooks/use-toast";
import { Link } from "react-router-dom";
import { API_ENDPOINTS } from "@/config/api";

interface Song {
  id: string;
  title: string;
  artist: string;
  cover: string | null;
  audioUrl: string;
  duration: number | null;
  votes: number;
  rank: number;
}

interface ApiSong {
  id: number;
  title: string;
  audio_url: string;
  cover_image: string | null;
  duration: number | null;
  vote_count: number;
  artist?: {
    stage_name: string;
    profile_image: string | null;
  } | null;
}

const resolveMediaUrl = (url: string | null | undefined) => {
  if (!url) return null;
  return new URL(url, new URL(API_ENDPOINTS.SONGS.BASE).origin).toString();
};

const fetchFeaturedSongs = async (signal?: AbortSignal): Promise<Song[]> => {
  const response = await fetch(API_ENDPOINTS.SONGS.BASE, { signal });
  if (!response.ok) throw new Error("Could not load current contenders.");

  const data = await response.json() as { songs: ApiSong[] };
  return data.songs.slice(0, 4).map((song, index) => ({
    id: String(song.id),
    title: song.title,
    artist: song.artist?.stage_name || "Unknown artist",
    cover: resolveMediaUrl(song.cover_image || song.artist?.profile_image),
    audioUrl: resolveMediaUrl(song.audio_url) || song.audio_url,
    duration: song.duration,
    votes: song.vote_count || 0,
    rank: index + 1,
  }));
};

const getRankBadge = (rank: number) => {
  switch (rank) {
    case 1:
      return "bg-gradient-gold text-black";
    case 2:
      return "bg-gradient-silver text-black";
    case 3:
      return "bg-gradient-bronze text-white";
    default:
      return "bg-muted text-muted-foreground";
  }
};

const formatDuration = (duration: number | null) => {
  if (duration === null) return null;
  const minutes = Math.floor(duration / 60);
  return `${minutes}:${String(duration % 60).padStart(2, "0")}`;
};

export const FeaturedSongs = () => {
  const [playingId, setPlayingId] = useState<string | null>(null);
  const [songs, setSongs] = useState<Song[]>([]);
  const [songsLoading, setSongsLoading] = useState(true);
  const [songsError, setSongsError] = useState("");
  const audioElements = useRef(new Map<string, HTMLAudioElement>());
  const { voteInfo, castVote, isLoading, isVoteDisabled } = useVoting();
  const { toast } = useToast();

  useEffect(() => {
    const controller = new AbortController();
    fetchFeaturedSongs(controller.signal)
      .then(setSongs)
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setSongsError(error instanceof Error ? error.message : "Could not load current contenders.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setSongsLoading(false);
      });

    return () => controller.abort();
  }, []);

  const refreshSongs = async () => {
    try {
      setSongs(await fetchFeaturedSongs());
      setSongsError("");
    } catch {
      setSongsError("Could not refresh contender votes.");
    }
  };

  const handlePlayback = async (song: Song) => {
    const audio = audioElements.current.get(song.id);
    if (!audio) return;

    if (playingId === song.id) {
      audio.pause();
      setPlayingId(null);
      return;
    }

    audioElements.current.forEach((element) => element.pause());
    try {
      await audio.play();
      setPlayingId(song.id);
    } catch {
      toast({
        title: "Playback failed",
        description: "This track could not be played right now.",
        variant: "destructive",
      });
    }
  };

  const handleVote = async (songId: string) => {
    // Security: Prevent voting if already voted
    if (isVoteDisabled) {
      toast({
        title: "Already Voted",
        description: "You have already cast your vote in this contest. Only one vote per user is allowed.",
        variant: "destructive",
      });
      return;
    }

    const result = await castVote(songId);
    
    if (result.success) {
      void refreshSongs();
      toast({
        title: "Vote Cast Successfully!",
        description: "Thank you for voting. Your vote has been recorded.",
      });
    } else {
      toast({
        title: "Vote Failed",
        description: result.error || "Unable to cast vote. Please try again.",
        variant: "destructive",
      });
    }
  };

  const getVoteButtonContent = (songId: string) => {
    if (voteInfo.hasVoted && voteInfo.votedSongId === songId) {
      return (
        <>
          <Check className="w-4 h-4" />
          Voted
        </>
      );
    }
    
    if (isVoteDisabled) {
      return (
        <>
          <Lock className="w-4 h-4" />
          Locked
        </>
      );
    }
    
    return (
      <>
        <Heart className="w-4 h-4" />
        Vote
      </>
    );
  };

  return (
    <section className="py-20 relative">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <h2 className="font-display text-3xl md:text-4xl font-bold mb-4">
            Top <span className="text-gradient-primary">Contenders</span>
          </h2>
          <p className="text-muted-foreground max-w-xl mx-auto">
            Listen to the songs leading the competition and cast your vote
          </p>
          {isVoteDisabled && (
            <p className="text-sm text-primary mt-2">
              ✓ You have already voted in this contest
            </p>
          )}
        </motion.div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {songsLoading ? (
            <p className="col-span-full py-10 text-center text-muted-foreground" role="status">
              Loading current contenders...
            </p>
          ) : songsError ? (
            <div className="col-span-full py-10 text-center" role="alert">
              <p className="text-muted-foreground">{songsError}</p>
              <Button variant="outline" className="mt-3" onClick={refreshSongs}>Try again</Button>
            </div>
          ) : songs.length === 0 ? (
            <p className="col-span-full py-10 text-center text-muted-foreground">
              No approved songs in the current contest yet.
            </p>
          ) : songs.map((song, index) => (
            <motion.div
              key={song.id}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1 }}
              className={`group glass rounded-2xl p-4 hover:glow-primary transition-all duration-500 ${
                voteInfo.votedSongId === song.id ? "ring-2 ring-primary" : ""
              }`}
            >
              {/* Cover */}
              <div className="relative mb-4 rounded-xl overflow-hidden aspect-square">
                {song.cover ? (
                  <img
                    src={song.cover}
                    alt={`${song.artist} artwork`}
                    className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                  />
                ) : (
                  <div className="w-full h-full bg-gradient-primary flex items-center justify-center">
                    <Music2 className="w-16 h-16 text-primary-foreground/80" />
                  </div>
                )}
                <audio
                  ref={(element) => {
                    if (element) audioElements.current.set(song.id, element);
                    else audioElements.current.delete(song.id);
                  }}
                  src={song.audioUrl}
                  preload="none"
                  onEnded={() => setPlayingId((current) => current === song.id ? null : current)}
                  className="hidden"
                />
                <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <button
                    onClick={() => void handlePlayback(song)}
                    aria-label={`${playingId === song.id ? "Pause" : "Play"} ${song.title}`}
                    className="w-14 h-14 rounded-full bg-primary flex items-center justify-center hover:scale-110 transition-transform"
                  >
                    {playingId === song.id ? (
                      <Pause className="w-6 h-6 text-primary-foreground" />
                    ) : (
                      <Play className="w-6 h-6 text-primary-foreground ml-1" />
                    )}
                  </button>
                </div>
                
                {/* Rank Badge */}
                <div className={`absolute top-3 left-3 w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${getRankBadge(song.rank)}`}>
                  {song.rank}
                </div>

                {/* Voted Badge */}
                {voteInfo.votedSongId === song.id && (
                  <div className="absolute top-3 right-3 bg-primary text-primary-foreground px-2 py-1 rounded-full text-xs font-bold flex items-center gap-1">
                    <Check className="w-3 h-3" />
                    Your Vote
                  </div>
                )}
              </div>

              {/* Info */}
              <h3 className="font-semibold text-foreground truncate">{song.title}</h3>
              <div className="flex items-center justify-between gap-2 mb-3">
                <p className="text-sm text-muted-foreground truncate">{song.artist}</p>
                {formatDuration(song.duration) && (
                  <span className="shrink-0 flex items-center gap-1 text-xs text-muted-foreground">
                    <Clock className="w-3.5 h-3.5" />
                    {formatDuration(song.duration)}
                  </span>
                )}
              </div>

              {/* Vote Count & Button */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1 text-sm text-muted-foreground">
                  <Trophy className="w-4 h-4 text-primary" />
                  <span>{song.votes.toLocaleString()}</span>
                </div>
                <Button 
                  variant={voteInfo.votedSongId === song.id ? "default" : "vote"} 
                  size="sm"
                  onClick={() => handleVote(song.id)}
                  disabled={isLoading || isVoteDisabled}
                  className={voteInfo.votedSongId === song.id ? "bg-primary" : ""}
                >
                  {getVoteButtonContent(song.id)}
                </Button>
              </div>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="text-center mt-10"
        >
          <Link to="/leaderboard">
            <Button variant="heroOutline" size="lg">
              View Full Leaderboard
            </Button>
          </Link>
        </motion.div>
      </div>
    </section>
  );
};
