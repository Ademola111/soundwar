import { motion } from "framer-motion";
import { Check, Heart, Lock, Music, Music2, RefreshCw, Users, Trophy } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { API_ENDPOINTS } from "@/config/api";
import { useAuth } from "@/contexts/AuthContext";
import { useVoting } from "@/hooks/useVoting";
import { useToast } from "@/hooks/use-toast";

interface Artist {
  id: string;
  songId: string;
  name: string;
  avatar: string | null;
  genre: string | null;
  songTitle: string;
  songCover: string | null;
  votes: number;
  rank: number;
}

interface ApiSong {
  id: number;
  artist_id: number;
  title: string;
  cover_image: string | null;
  vote_count: number;
  artist?: {
    id: number;
    stage_name: string;
    profile_image: string | null;
    genre?: string | null;
  } | null;
}

const resolveMediaUrl = (url: string | null | undefined) => {
  if (!url) return null;
  return new URL(url, new URL(API_ENDPOINTS.SONGS.BASE).origin).toString();
};

const fetchCompetitors = async (): Promise<Artist[]> => {
  const response = await fetch(API_ENDPOINTS.SONGS.BASE);
  if (!response.ok) throw new Error("Could not load competitors for the active contest.");

  const data = await response.json() as { songs: ApiSong[] };
  return data.songs.map((song, index) => ({
    id: String(song.artist?.id || song.artist_id),
    songId: String(song.id),
    name: song.artist?.stage_name || "Unknown artist",
    avatar: resolveMediaUrl(song.artist?.profile_image),
    genre: song.artist?.genre || null,
    songTitle: song.title,
    songCover: resolveMediaUrl(song.cover_image || song.artist?.profile_image),
    votes: song.vote_count || 0,
    rank: index + 1,
  }));
};

const Artists = () => {
  const { data: artists = [], isLoading, isError, error, refetch } = useQuery({
    queryKey: ["competitors"],
    queryFn: fetchCompetitors,
    refetchInterval: 30_000,
  });
  const { isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const { voteInfo, castVote, isLoading: isVoting, isVoteDisabled } = useVoting();
  const { toast } = useToast();

  const handleVote = async (songId: string) => {
    const result = await castVote(songId);
    if (!result.success) {
      toast({
        title: "Vote failed",
        description: result.error || "Unable to cast your vote.",
        variant: "destructive",
      });
      return;
    }

    await refetch();
    toast({ title: "Vote recorded", description: "Thank you for supporting this artist." });
  };

  const getVoteButton = (songId: string) => {
    if (voteInfo.votedSongId === songId) {
      return <Button variant="default" size="sm" disabled className="bg-primary"><Check className="w-4 h-4 mr-1" />Voted</Button>;
    }
    if (isVoteDisabled) {
      return <Button variant="outline" size="sm" disabled><Lock className="w-4 h-4 mr-1" />Locked</Button>;
    }
    return (
      <Button variant="vote" size="sm" onClick={() => void handleVote(songId)} disabled={isVoting}>
        <Heart className="w-4 h-4 mr-1" />Vote Now
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
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-accent/20 text-accent mb-6">
              <Users className="w-4 h-4" />
              <span className="text-sm font-semibold">Featured Artists</span>
            </div>
            <h1 className="font-display text-4xl md:text-5xl font-bold mb-4">
              Meet the <span className="text-gradient-accent">Competitors</span>
            </h1>
            <p className="text-muted-foreground max-w-xl mx-auto">
              Discover talented artists competing for the SoundWars crown
            </p>
          </motion.div>

          {/* Artists Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
            {isLoading ? (
              <p className="col-span-full py-12 text-center text-muted-foreground" role="status">Loading current competitors...</p>
            ) : isError ? (
              <div className="col-span-full py-12 text-center" role="alert">
                <p className="text-muted-foreground">
                  {error instanceof Error ? error.message : "Could not load current competitors."}
                </p>
                <Button variant="outline" className="mt-4" onClick={() => void refetch()}>
                  <RefreshCw className="w-4 h-4 mr-2" />Try again
                </Button>
              </div>
            ) : artists.length === 0 ? (
              <div className="col-span-full py-12 text-center text-muted-foreground">
                <Users className="w-10 h-10 mx-auto mb-3 opacity-60" />
                <p className="font-medium text-foreground">No competitors yet</p>
                <p className="text-sm mt-1">Approved song submissions will appear here during the active contest.</p>
              </div>
            ) : artists.map((artist, index) => (
              <motion.div
                key={artist.id}
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="glass rounded-2xl overflow-hidden group hover:glow-accent transition-all duration-500"
              >
                {/* Song Cover Background */}
                <div className="relative h-40">
                  {artist.songCover ? (
                    <img
                      src={artist.songCover}
                      alt={`${artist.songTitle} cover art`}
                      className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                    />
                  ) : (
                    <div className="w-full h-full bg-primary/10 flex items-center justify-center">
                      <Music2 className="w-12 h-12 text-primary" />
                    </div>
                  )}
                  <div className="absolute inset-0 bg-gradient-to-t from-background to-transparent" />
                  
                  {/* Rank Badge */}
                  {artist.rank <= 3 && (
                    <div className={`absolute top-4 right-4 w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                      artist.rank === 1 ? "bg-gradient-to-r from-[hsl(45,100%,50%)] to-[hsl(35,100%,45%)] text-black" :
                      artist.rank === 2 ? "bg-gradient-to-r from-[hsl(220,10%,70%)] to-[hsl(220,10%,55%)] text-black" :
                      "bg-gradient-to-r from-[hsl(25,70%,50%)] to-[hsl(15,70%,40%)] text-white"
                    }`}>
                      <Trophy className="w-5 h-5" />
                    </div>
                  )}
                </div>

                {/* Artist Info */}
                <div className="p-6 -mt-12 relative">
                  {artist.avatar ? (
                    <img
                      src={artist.avatar}
                      alt={artist.name}
                      className="w-20 h-20 rounded-full border-4 border-background object-cover mb-4"
                    />
                  ) : (
                    <div className="w-20 h-20 rounded-full border-4 border-background bg-accent/20 flex items-center justify-center mb-4">
                      <Users className="w-8 h-8 text-accent" />
                    </div>
                  )}
                  <h3 className="font-display text-xl font-bold mb-1">{artist.name}</h3>
                  <span className="inline-block px-3 py-1 rounded-full bg-primary/20 text-primary text-xs font-semibold mb-4">
                    {artist.genre || "Genre not specified"}
                  </span>
                  
                  {/* Song Info */}
                  <div className="flex items-center gap-2 text-muted-foreground mb-4">
                    <Music className="w-4 h-4" />
                    <span className="text-sm">{artist.songTitle}</span>
                  </div>

                  {/* Stats & Action */}
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-2xl font-display font-bold text-primary">
                        {artist.votes.toLocaleString()}
                      </div>
                      <p className="text-xs text-muted-foreground">votes received</p>
                    </div>
                    {getVoteButton(artist.songId)}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          {/* CTA */}
          {!isAuthLoading && !isAuthenticated && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6 }}
              className="text-center mt-12"
            >
              <p className="text-muted-foreground mb-4">Are you an artist?</p>
              <Link to="/register">
                <Button variant="hero" size="lg">
                  Join the Competition
                </Button>
              </Link>
            </motion.div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
};

export default Artists;
