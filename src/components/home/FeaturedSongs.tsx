import { motion } from "framer-motion";
import { Play, Pause, Heart, Trophy, Check, Lock } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useVoting } from "@/hooks/useVoting";
import { useToast } from "@/hooks/use-toast";
import { Link } from "react-router-dom";

interface Song {
  id: string;
  title: string;
  artist: string;
  cover: string;
  votes: number;
  rank: number;
}

const mockSongs: Song[] = [
  {
    id: "1",
    title: "Midnight Dreams",
    artist: "Luna Wave",
    cover: "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=400&h=400&fit=crop",
    votes: 2847,
    rank: 1,
  },
  {
    id: "2",
    title: "Electric Soul",
    artist: "Neon Beats",
    cover: "https://images.unsplash.com/photo-1514320291840-2e0a9bf2a9ae?w=400&h=400&fit=crop",
    votes: 2456,
    rank: 2,
  },
  {
    id: "3",
    title: "Starlight",
    artist: "Cosmic Echo",
    cover: "https://images.unsplash.com/photo-1511379938547-c1f69419868d?w=400&h=400&fit=crop",
    votes: 2134,
    rank: 3,
  },
  {
    id: "4",
    title: "Urban Rhythm",
    artist: "Street Harmony",
    cover: "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=400&h=400&fit=crop",
    votes: 1987,
    rank: 4,
  },
];

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

export const FeaturedSongs = () => {
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
          {mockSongs.map((song, index) => (
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
                <img
                  src={song.cover}
                  alt={song.title}
                  className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                />
                <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <button
                    onClick={() => setPlayingId(playingId === song.id ? null : song.id)}
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
              <p className="text-sm text-muted-foreground truncate mb-3">{song.artist}</p>

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
