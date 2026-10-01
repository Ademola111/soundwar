import { motion } from "framer-motion";
import { Trophy, Play, Pause, TrendingUp, TrendingDown, Minus, Check, Lock, Heart, Music2, RefreshCw } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { useVoting } from "@/hooks/useVoting";
import { useToast } from "@/hooks/use-toast";
import { API_ENDPOINTS } from "@/config/api";
import { useQuery } from "@tanstack/react-query";

interface Song {
  id: string;
  rank: number;
  previousRank: number;
  title: string;
  artist: string;
  artistAvatar: string | null;
  cover: string | null;
  audioUrl: string;
  duration: number | null;
  votes: number;
  percentageOfTotal: number;
}

interface ApiLeaderboardSong {
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

interface ApiLeaderboardResponse {
  leaderboard: Array<{
    rank: number;
    vote_count: number;
    song: ApiLeaderboardSong;
  }>;
  contest: { title: string; phase: string } | null;
}

const resolveMediaUrl = (url: string | null | undefined) => {
  if (!url) return null;
  return new URL(url, new URL(API_ENDPOINTS.SONGS.BASE).origin).toString();
};

const fetchLeaderboard = async (signal?: AbortSignal) => {
  const response = await fetch(API_ENDPOINTS.LEADERBOARD.BASE, { signal });
  if (!response.ok) throw new Error("Could not load the competition leaderboard.");

  const data = await response.json() as ApiLeaderboardResponse;
  const totalVotes = data.leaderboard.reduce((total, item) => total + item.vote_count, 0);
  const songs = data.leaderboard.map(({ rank, vote_count, song }) => ({
    id: String(song.id),
    rank,
    previousRank: rank,
    title: song.title,
    artist: song.artist?.stage_name || "Unknown artist",
    artistAvatar: resolveMediaUrl(song.artist?.profile_image),
    cover: resolveMediaUrl(song.cover_image || song.artist?.profile_image),
    audioUrl: resolveMediaUrl(song.audio_url) || song.audio_url,
    duration: song.duration,
    votes: vote_count,
    percentageOfTotal: totalVotes ? Math.round((vote_count / totalVotes) * 1000) / 10 : 0,
  }));

  return { songs, contest: data.contest };
};

const getRankStyles = (rank: number) => {
  switch (rank) {
    case 1:
      return "bg-gradient-to-r from-[hsl(45,100%,50%)] to-[hsl(35,100%,45%)] text-black";
    case 2:
      return "bg-gradient-to-r from-[hsl(220,10%,70%)] to-[hsl(220,10%,55%)] text-black";
    case 3:
      return "bg-gradient-to-r from-[hsl(25,70%,50%)] to-[hsl(15,70%,40%)] text-white";
    default:
      return "bg-muted text-muted-foreground";
  }
};

const getTrendIcon = (current: number, previous: number) => {
  if (current < previous) return <TrendingUp className="w-4 h-4 text-green-500" />;
  if (current > previous) return <TrendingDown className="w-4 h-4 text-red-500" />;
  return <Minus className="w-4 h-4 text-muted-foreground" />;
};

const Leaderboard = () => {
  const [playingId, setPlayingId] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const { voteInfo, castVote, isLoading, isVoteDisabled } = useVoting();
  const { toast } = useToast();
  const {
    data: leaderboardData,
    isLoading: isLoadingLeaderboard,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["leaderboard"],
    queryFn: () => fetchLeaderboard(),
    refetchInterval: 30_000,
  });
  const leaderboard = leaderboardData?.songs || [];
  const podiumSongs = leaderboard.length >= 3
    ? [leaderboard[1], leaderboard[0], leaderboard[2]]
    : leaderboard.slice(0, 3);

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
      await refetch();
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

  const handlePlayback = async (song: Song) => {
    const audio = audioRef.current;
    if (!audio) return;

    if (playingId === song.id) {
      audio.pause();
      setPlayingId(null);
      return;
    }

    audio.pause();
    audio.src = song.audioUrl;
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

  const getVoteButton = (songId: string) => {
    if (voteInfo.hasVoted && voteInfo.votedSongId === songId) {
      return (
        <Button variant="default" size="sm" disabled className="bg-primary">
          <Check className="w-4 h-4 mr-1" />
          Voted
        </Button>
      );
    }
    
    if (isVoteDisabled) {
      return (
        <Button variant="outline" size="sm" disabled className="opacity-50">
          <Lock className="w-4 h-4 mr-1" />
          Locked
        </Button>
      );
    }
    
    return (
      <Button 
        variant="vote" 
        size="sm"
        onClick={() => handleVote(songId)}
        disabled={isLoading}
      >
        <Heart className="w-4 h-4 mr-1" />
        Vote
      </Button>
    );
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="pt-24 pb-20">
        <div className="container mx-auto px-4">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-12"
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/20 text-primary mb-6">
              <Trophy className="w-4 h-4" />
              <span className="text-sm font-semibold">Live Rankings</span>
            </div>
            <h1 className="font-display text-4xl md:text-5xl font-bold mb-4">
              Competition <span className="text-gradient-primary">Leaderboard</span>
            </h1>
            <p className="text-muted-foreground max-w-xl mx-auto">
              {leaderboardData?.contest
                ? `${leaderboardData.contest.title} · updated live`
                : "See which tracks are leading the competition in real-time"}
            </p>
            {isVoteDisabled && (
              <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary">
                <Check className="w-4 h-4" />
                <span className="text-sm font-medium">You have already voted in this contest</span>
              </div>
            )}
          </motion.div>

          {isLoadingLeaderboard ? (
            <p className="py-12 text-center text-muted-foreground" role="status">Loading live rankings...</p>
          ) : isError ? (
            <div className="py-12 text-center" role="alert">
              <p className="text-muted-foreground">
                {error instanceof Error ? error.message : "Could not load the competition leaderboard."}
              </p>
              <Button variant="outline" className="mt-4" onClick={() => void refetch()}>
                <RefreshCw className="w-4 h-4 mr-2" /> Try again
              </Button>
            </div>
          ) : leaderboard.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              <Trophy className="w-10 h-10 mx-auto mb-3 opacity-60" />
              <p className="font-medium text-foreground">No approved songs yet</p>
              <p className="text-sm mt-1">Rankings will appear when tracks are approved for the active contest.</p>
            </div>
          ) : (
          <>
          {/* Top 3 Podium */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12 max-w-4xl mx-auto"
          >
            {podiumSongs.map((displaySong, index) => {
              const isFirst = displaySong.rank === 1;
              const isVotedSong = voteInfo.votedSongId === displaySong.id;
              
              return (
                <motion.div
                  key={displaySong.id}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.2 + index * 0.1 }}
                  className={`glass rounded-2xl p-6 text-center ${isFirst ? "md:-mt-8 glow-primary" : ""} ${isVotedSong ? "ring-2 ring-primary" : ""}`}
                >
                  <div className={`w-12 h-12 mx-auto rounded-full flex items-center justify-center font-bold text-lg mb-4 ${getRankStyles(displaySong.rank)}`}>
                    {displaySong.rank}
                  </div>
                  <div className="relative">
                    {displaySong.cover ? (
                      <img
                        src={displaySong.cover}
                        alt={`${displaySong.title} cover art`}
                        className={`w-24 h-24 mx-auto rounded-xl object-cover mb-4 ${isFirst ? "ring-4 ring-primary/50" : ""}`}
                      />
                    ) : (
                      <div className={`w-24 h-24 mx-auto rounded-xl bg-primary/10 flex items-center justify-center mb-4 ${isFirst ? "ring-4 ring-primary/50" : ""}`}>
                        <Music2 className="w-9 h-9 text-primary" />
                      </div>
                    )}
                    <button
                      type="button"
                      onClick={() => void handlePlayback(displaySong)}
                      aria-label={`${playingId === displaySong.id ? "Pause" : "Play"} ${displaySong.title}`}
                      className="absolute bottom-6 right-[calc(50%-3.5rem)] w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center"
                    >
                      {playingId === displaySong.id ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
                    </button>
                    {isVotedSong && (
                      <div className="absolute -top-2 -right-2 bg-primary text-primary-foreground w-8 h-8 rounded-full flex items-center justify-center">
                        <Check className="w-4 h-4" />
                      </div>
                    )}
                  </div>
                  <h3 className="font-semibold text-lg">{displaySong.title}</h3>
                  <p className="text-muted-foreground text-sm mb-3">{displaySong.artist}</p>
                  <div className="text-2xl font-display font-bold text-primary">
                    {displaySong.votes.toLocaleString()}
                  </div>
                  <p className="text-xs text-muted-foreground mb-3">votes</p>
                  {getVoteButton(displaySong.id)}
                </motion.div>
              );
            })}
          </motion.div>

          {/* Full Leaderboard */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="max-w-4xl mx-auto"
          >
            <div className="glass rounded-2xl overflow-hidden">
              <div className="grid grid-cols-12 gap-4 p-4 border-b border-border text-sm font-semibold text-muted-foreground">
                <div className="col-span-1">#</div>
                <div className="col-span-1"></div>
                <div className="col-span-5">Song</div>
                <div className="col-span-2 text-center">Trend</div>
                <div className="col-span-2 text-right">Votes</div>
                <div className="col-span-1"></div>
              </div>
              
              {leaderboard.map((song, index) => {
                const isVotedSong = voteInfo.votedSongId === song.id;
                
                return (
                  <motion.div
                    key={song.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.5 + index * 0.05 }}
                    className={`grid grid-cols-12 gap-4 p-4 items-center border-b border-border/50 hover:bg-muted/30 transition-colors ${isVotedSong ? "bg-primary/5" : ""}`}
                  >
                    <div className={`col-span-1 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${getRankStyles(song.rank)}`}>
                      {song.rank}
                    </div>
                    <div className="col-span-1">
                      <button
                        onClick={() => void handlePlayback(song)}
                        aria-label={`${playingId === song.id ? "Pause" : "Play"} ${song.title}`}
                        className="w-10 h-10 rounded-full bg-primary/20 hover:bg-primary flex items-center justify-center transition-colors group"
                      >
                        {playingId === song.id ? (
                          <Pause className="w-4 h-4 text-primary group-hover:text-primary-foreground" />
                        ) : (
                          <Play className="w-4 h-4 text-primary group-hover:text-primary-foreground ml-0.5" />
                        )}
                      </button>
                    </div>
                    <div className="col-span-5 flex items-center gap-3">
                      <div className="relative">
                        {song.cover ? (
                          <img src={song.cover} alt={`${song.title} cover art`} className="w-12 h-12 rounded-lg object-cover" />
                        ) : (
                          <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                            <Music2 className="w-5 h-5 text-primary" />
                          </div>
                        )}
                        {isVotedSong && (
                          <div className="absolute -top-1 -right-1 bg-primary text-primary-foreground w-5 h-5 rounded-full flex items-center justify-center">
                            <Check className="w-3 h-3" />
                          </div>
                        )}
                      </div>
                      <div>
                        <h4 className="font-semibold">{song.title}</h4>
                        <p className="text-sm text-muted-foreground">{song.artist}</p>
                      </div>
                    </div>
                    <div className="col-span-2 flex justify-center items-center gap-1">
                      {getTrendIcon(song.rank, song.previousRank)}
                      <span className="text-xs text-muted-foreground">
                        {Math.abs(song.rank - song.previousRank) || "—"}
                      </span>
                    </div>
                    <div className="col-span-2 text-right">
                      <div className="font-semibold">{song.votes.toLocaleString()}</div>
                      <div className="text-xs text-muted-foreground">{song.percentageOfTotal}%</div>
                    </div>
                    <div className="col-span-1">
                      {getVoteButton(song.id)}
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
          </>
          )}
          <audio ref={audioRef} className="hidden" onEnded={() => setPlayingId(null)} />
        </div>
      </main>
      <Footer />
    </div>
  );
};

export default Leaderboard;
