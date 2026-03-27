import { motion } from "framer-motion";
import { Trophy, Play, Pause, TrendingUp, TrendingDown, Minus, Check, Lock, Heart } from "lucide-react";
import { useState } from "react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { useVoting } from "@/hooks/useVoting";
import { useToast } from "@/hooks/use-toast";

interface Song {
  id: string;
  rank: number;
  previousRank: number;
  title: string;
  artist: string;
  artistAvatar: string;
  cover: string;
  votes: number;
  percentageOfTotal: number;
}

const mockLeaderboard: Song[] = [
  {
    id: "1",
    rank: 1,
    previousRank: 1,
    title: "Midnight Dreams",
    artist: "Luna Wave",
    artistAvatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop",
    cover: "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=400&h=400&fit=crop",
    votes: 2847,
    percentageOfTotal: 18.5,
  },
  {
    id: "2",
    rank: 2,
    previousRank: 3,
    title: "Electric Soul",
    artist: "Neon Beats",
    artistAvatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop",
    cover: "https://images.unsplash.com/photo-1514320291840-2e0a9bf2a9ae?w=400&h=400&fit=crop",
    votes: 2456,
    percentageOfTotal: 15.9,
  },
  {
    id: "3",
    rank: 3,
    previousRank: 2,
    title: "Starlight",
    artist: "Cosmic Echo",
    artistAvatar: "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&h=100&fit=crop",
    cover: "https://images.unsplash.com/photo-1511379938547-c1f69419868d?w=400&h=400&fit=crop",
    votes: 2134,
    percentageOfTotal: 13.8,
  },
  {
    id: "4",
    rank: 4,
    previousRank: 5,
    title: "Urban Rhythm",
    artist: "Street Harmony",
    artistAvatar: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop",
    cover: "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=400&h=400&fit=crop",
    votes: 1987,
    percentageOfTotal: 12.9,
  },
  {
    id: "5",
    rank: 5,
    previousRank: 4,
    title: "Ocean Waves",
    artist: "Surf Sound",
    artistAvatar: "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=100&h=100&fit=crop",
    cover: "https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=400&h=400&fit=crop",
    votes: 1756,
    percentageOfTotal: 11.4,
  },
];

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
  const { voteInfo, castVote, isLoading, isVoteDisabled } = useVoting();
  const { toast } = useToast();

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
              See which tracks are leading the competition in real-time
            </p>
            {isVoteDisabled && (
              <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary">
                <Check className="w-4 h-4" />
                <span className="text-sm font-medium">You have already voted in this contest</span>
              </div>
            )}
          </motion.div>

          {/* Top 3 Podium */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12 max-w-4xl mx-auto"
          >
            {mockLeaderboard.slice(0, 3).map((song, index) => {
              const order = [1, 0, 2]; // Center is first place
              const displaySong = mockLeaderboard[order[index]];
              const isFirst = order[index] === 0;
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
                    <img
                      src={displaySong.cover}
                      alt={displaySong.title}
                      className={`w-24 h-24 mx-auto rounded-xl object-cover mb-4 ${isFirst ? "ring-4 ring-primary/50" : ""}`}
                    />
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
              
              {mockLeaderboard.map((song, index) => {
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
                        onClick={() => setPlayingId(playingId === song.id ? null : song.id)}
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
                        <img
                          src={song.cover}
                          alt={song.title}
                          className="w-12 h-12 rounded-lg object-cover"
                        />
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
        </div>
      </main>
      <Footer />
    </div>
  );
};

export default Leaderboard;
