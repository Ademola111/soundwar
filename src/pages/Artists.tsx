import { motion } from "framer-motion";
import { Music, Users, Trophy } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";

interface Artist {
  id: string;
  name: string;
  avatar: string;
  genre: string;
  songTitle: string;
  songCover: string;
  votes: number;
  rank: number;
}

const mockArtists: Artist[] = [
  {
    id: "1",
    name: "Luna Wave",
    avatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200&h=200&fit=crop",
    genre: "Electronic",
    songTitle: "Midnight Dreams",
    songCover: "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=400&h=400&fit=crop",
    votes: 2847,
    rank: 1,
  },
  {
    id: "2",
    name: "Neon Beats",
    avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&h=200&fit=crop",
    genre: "Pop",
    songTitle: "Electric Soul",
    songCover: "https://images.unsplash.com/photo-1514320291840-2e0a9bf2a9ae?w=400&h=400&fit=crop",
    votes: 2456,
    rank: 2,
  },
  {
    id: "3",
    name: "Cosmic Echo",
    avatar: "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=200&h=200&fit=crop",
    genre: "Indie",
    songTitle: "Starlight",
    songCover: "https://images.unsplash.com/photo-1511379938547-c1f69419868d?w=400&h=400&fit=crop",
    votes: 2134,
    rank: 3,
  },
  {
    id: "4",
    name: "Street Harmony",
    avatar: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=200&h=200&fit=crop",
    genre: "Hip-Hop",
    songTitle: "Urban Rhythm",
    songCover: "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=400&h=400&fit=crop",
    votes: 1987,
    rank: 4,
  },
  {
    id: "5",
    name: "Surf Sound",
    avatar: "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=200&h=200&fit=crop",
    genre: "Chill",
    songTitle: "Ocean Waves",
    songCover: "https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=400&h=400&fit=crop",
    votes: 1756,
    rank: 5,
  },
  {
    id: "6",
    name: "Night Owl",
    avatar: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=200&h=200&fit=crop",
    genre: "R&B",
    songTitle: "Late Night Vibes",
    songCover: "https://images.unsplash.com/photo-1484972759836-b93f9ef2b293?w=400&h=400&fit=crop",
    votes: 1523,
    rank: 6,
  },
];

const Artists = () => {
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
            {mockArtists.map((artist, index) => (
              <motion.div
                key={artist.id}
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="glass rounded-2xl overflow-hidden group hover:glow-accent transition-all duration-500"
              >
                {/* Song Cover Background */}
                <div className="relative h-40">
                  <img
                    src={artist.songCover}
                    alt={artist.songTitle}
                    className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                  />
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
                  <img
                    src={artist.avatar}
                    alt={artist.name}
                    className="w-20 h-20 rounded-full border-4 border-background object-cover mb-4"
                  />
                  <h3 className="font-display text-xl font-bold mb-1">{artist.name}</h3>
                  <span className="inline-block px-3 py-1 rounded-full bg-primary/20 text-primary text-xs font-semibold mb-4">
                    {artist.genre}
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
                    <Button variant="vote" size="sm">
                      Vote Now
                    </Button>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          {/* CTA */}
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
        </div>
      </main>
      <Footer />
    </div>
  );
};

export default Artists;
