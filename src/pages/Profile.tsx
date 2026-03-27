import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { 
  User, 
  Music, 
  Vote, 
  TrendingUp, 
  DollarSign, 
  Calendar,
  Play,
  Heart,
  Award,
  Settings,
  LogOut
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { API_ENDPOINTS, getAuthHeaders } from "@/config/api";

// Mock data for demo - will be replaced with API calls
const mockUser = {
  id: "1",
  email: "user@example.com",
  username: "musiclover",
  roles: ["user"] as const,
  created_at: "2024-01-15",
};

const mockArtist = {
  id: "2",
  email: "artist@example.com",
  username: "starproducer",
  roles: ["artist"] as const,
  artist_profile: {
    id: "a1",
    stage_name: "Star Producer",
    bio: "Award-winning producer with 10+ years of experience",
    avatar_url: "",
    total_votes: 1250,
    total_earnings: 2500,
  },
  created_at: "2024-01-10",
};

const mockVotingHistory = [
  { id: "1", song_title: "Midnight Dreams", artist_name: "Luna Echo", voted_at: "2024-03-15", position: 3 },
  { id: "2", song_title: "Electric Soul", artist_name: "Neon Pulse", voted_at: "2024-03-10", position: 7 },
  { id: "3", song_title: "Ocean Waves", artist_name: "Tide Master", voted_at: "2024-03-05", position: 12 },
  { id: "4", song_title: "City Lights", artist_name: "Metro Beat", voted_at: "2024-02-28", position: 5 },
];

const mockArtistSongs = [
  { id: "1", title: "Summer Vibes", plays: 15420, votes: 342, status: "approved", earnings: 850, uploaded_at: "2024-02-01" },
  { id: "2", title: "Moonlight Sonata Remix", plays: 8930, votes: 189, status: "approved", earnings: 472, uploaded_at: "2024-02-15" },
  { id: "3", title: "Urban Jungle", plays: 0, votes: 0, status: "pending", earnings: 0, uploaded_at: "2024-03-18" },
];

const Profile = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");
  
  // For demo purposes, toggle between user and artist view
  const [demoRole, setDemoRole] = useState<"user" | "artist">("artist");
  const isArtist = demoRole === "artist";
  const currentUser = isArtist ? mockArtist : mockUser;

  useEffect(() => {
    // Simulate loading
    const timer = setTimeout(() => setIsLoading(false), 500);
    return () => clearTimeout(timer);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("auth_token");
    navigate("/");
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "approved":
        return <Badge className="bg-primary/20 text-primary border-primary/30">Approved</Badge>;
      case "pending":
        return <Badge className="bg-yellow-500/20 text-yellow-400 border-yellow-500/30">Pending</Badge>;
      case "rejected":
        return <Badge className="bg-destructive/20 text-destructive border-destructive/30">Rejected</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-pulse text-primary">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      
      <main className="container mx-auto px-4 pt-24 pb-16">
        {/* Demo Toggle */}
        <div className="mb-6 p-4 glass rounded-lg">
          <p className="text-sm text-muted-foreground mb-2">Demo Mode: Switch view</p>
          <div className="flex gap-2">
            <Button 
              variant={demoRole === "user" ? "default" : "outline"} 
              size="sm"
              onClick={() => setDemoRole("user")}
            >
              Voter View
            </Button>
            <Button 
              variant={demoRole === "artist" ? "default" : "outline"} 
              size="sm"
              onClick={() => setDemoRole("artist")}
            >
              Artist View
            </Button>
          </div>
        </div>

        {/* Profile Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <Card className="glass border-border/50">
            <CardContent className="p-6">
              <div className="flex flex-col md:flex-row items-start md:items-center gap-6">
                <Avatar className="h-24 w-24 border-2 border-primary">
                  <AvatarImage src={isArtist ? mockArtist.artist_profile.avatar_url : ""} />
                  <AvatarFallback className="bg-primary/20 text-primary text-2xl">
                    {isArtist ? mockArtist.artist_profile.stage_name[0] : mockUser.username[0].toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h1 className="text-3xl font-bold">
                      {isArtist ? mockArtist.artist_profile.stage_name : mockUser.username}
                    </h1>
                    <Badge className={isArtist ? "bg-accent/20 text-accent" : "bg-primary/20 text-primary"}>
                      {isArtist ? "Artist" : "Voter"}
                    </Badge>
                  </div>
                  {isArtist && (
                    <p className="text-muted-foreground mb-3">{mockArtist.artist_profile.bio}</p>
                  )}
                  <p className="text-sm text-muted-foreground">
                    Member since {new Date(currentUser.created_at).toLocaleDateString()}
                  </p>
                </div>

                <div className="flex gap-2">
                  <Button variant="outline" size="sm">
                    <Settings className="h-4 w-4 mr-2" />
                    Settings
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleLogout}>
                    <LogOut className="h-4 w-4 mr-2" />
                    Logout
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Stats Cards */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8"
        >
          {isArtist ? (
            <>
              <Card className="glass border-border/50">
                <CardContent className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-primary/20">
                      <Music className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold">{mockArtistSongs.length}</p>
                      <p className="text-xs text-muted-foreground">Songs</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card className="glass border-border/50">
                <CardContent className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-accent/20">
                      <Heart className="h-5 w-5 text-accent" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold">{mockArtist.artist_profile.total_votes.toLocaleString()}</p>
                      <p className="text-xs text-muted-foreground">Total Votes</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card className="glass border-border/50">
                <CardContent className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-green-500/20">
                      <Play className="h-5 w-5 text-green-400" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold">
                        {mockArtistSongs.reduce((sum, s) => sum + s.plays, 0).toLocaleString()}
                      </p>
                      <p className="text-xs text-muted-foreground">Total Plays</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card className="glass border-border/50">
                <CardContent className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-yellow-500/20">
                      <DollarSign className="h-5 w-5 text-yellow-400" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold">${mockArtist.artist_profile.total_earnings.toLocaleString()}</p>
                      <p className="text-xs text-muted-foreground">Earnings</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          ) : (
            <>
              <Card className="glass border-border/50">
                <CardContent className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-primary/20">
                      <Vote className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold">{mockVotingHistory.length}</p>
                      <p className="text-xs text-muted-foreground">Votes Cast</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card className="glass border-border/50">
                <CardContent className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-accent/20">
                      <Award className="h-5 w-5 text-accent" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold">2</p>
                      <p className="text-xs text-muted-foreground">Winners Picked</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card className="glass border-border/50">
                <CardContent className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-green-500/20">
                      <TrendingUp className="h-5 w-5 text-green-400" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold">Top 10</p>
                      <p className="text-xs text-muted-foreground">Best Pick</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card className="glass border-border/50">
                <CardContent className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-yellow-500/20">
                      <Calendar className="h-5 w-5 text-yellow-400" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold">3</p>
                      <p className="text-xs text-muted-foreground">Contests</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </motion.div>

        {/* Content Tabs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="glass mb-6">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              {isArtist ? (
                <>
                  <TabsTrigger value="songs">My Songs</TabsTrigger>
                  <TabsTrigger value="earnings">Earnings</TabsTrigger>
                </>
              ) : (
                <TabsTrigger value="votes">Voting History</TabsTrigger>
              )}
            </TabsList>

            <TabsContent value="overview">
              <Card className="glass border-border/50">
                <CardHeader>
                  <CardTitle>{isArtist ? "Performance Overview" : "Activity Overview"}</CardTitle>
                </CardHeader>
                <CardContent>
                  {isArtist ? (
                    <div className="space-y-6">
                      <div>
                        <div className="flex justify-between mb-2">
                          <span className="text-sm text-muted-foreground">Contest Progress</span>
                          <span className="text-sm font-medium">65%</span>
                        </div>
                        <Progress value={65} className="h-2" />
                      </div>
                      <div className="grid md:grid-cols-2 gap-4">
                        <div className="p-4 rounded-lg bg-secondary/50">
                          <h4 className="font-medium mb-2">Top Performing Song</h4>
                          <p className="text-primary font-semibold">Summer Vibes</p>
                          <p className="text-sm text-muted-foreground">342 votes • 15.4k plays</p>
                        </div>
                        <div className="p-4 rounded-lg bg-secondary/50">
                          <h4 className="font-medium mb-2">Current Ranking</h4>
                          <p className="text-primary font-semibold">#5</p>
                          <p className="text-sm text-muted-foreground">Up 2 positions this week</p>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <p className="text-muted-foreground">
                        Your voting activity helps determine the winners of our music competitions.
                        Keep discovering and supporting great music!
                      </p>
                      <div className="p-4 rounded-lg bg-secondary/50">
                        <h4 className="font-medium mb-2">Your Latest Vote</h4>
                        <p className="text-primary font-semibold">{mockVotingHistory[0].song_title}</p>
                        <p className="text-sm text-muted-foreground">
                          by {mockVotingHistory[0].artist_name} • Currently #{mockVotingHistory[0].position}
                        </p>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {isArtist && (
              <>
                <TabsContent value="songs">
                  <Card className="glass border-border/50">
                    <CardHeader className="flex flex-row items-center justify-between">
                      <CardTitle>My Songs</CardTitle>
                      <Button onClick={() => navigate("/submit")}>
                        <Music className="h-4 w-4 mr-2" />
                        Submit New Song
                      </Button>
                    </CardHeader>
                    <CardContent>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Title</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead className="text-right">Plays</TableHead>
                            <TableHead className="text-right">Votes</TableHead>
                            <TableHead className="text-right">Earnings</TableHead>
                            <TableHead>Uploaded</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {mockArtistSongs.map((song) => (
                            <TableRow key={song.id}>
                              <TableCell className="font-medium">{song.title}</TableCell>
                              <TableCell>{getStatusBadge(song.status)}</TableCell>
                              <TableCell className="text-right">{song.plays.toLocaleString()}</TableCell>
                              <TableCell className="text-right">{song.votes.toLocaleString()}</TableCell>
                              <TableCell className="text-right">${song.earnings}</TableCell>
                              <TableCell className="text-muted-foreground">
                                {new Date(song.uploaded_at).toLocaleDateString()}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="earnings">
                  <Card className="glass border-border/50">
                    <CardHeader>
                      <CardTitle>Earnings Breakdown</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-6">
                        <div className="grid md:grid-cols-3 gap-4">
                          <div className="p-4 rounded-lg bg-secondary/50 text-center">
                            <p className="text-3xl font-bold text-primary">${mockArtist.artist_profile.total_earnings}</p>
                            <p className="text-sm text-muted-foreground">Total Earnings</p>
                          </div>
                          <div className="p-4 rounded-lg bg-secondary/50 text-center">
                            <p className="text-3xl font-bold text-green-400">$1,322</p>
                            <p className="text-sm text-muted-foreground">Available to Withdraw</p>
                          </div>
                          <div className="p-4 rounded-lg bg-secondary/50 text-center">
                            <p className="text-3xl font-bold text-yellow-400">$1,178</p>
                            <p className="text-sm text-muted-foreground">Already Withdrawn</p>
                          </div>
                        </div>
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Song</TableHead>
                              <TableHead className="text-right">Earnings</TableHead>
                              <TableHead>Period</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {mockArtistSongs.filter(s => s.earnings > 0).map((song) => (
                              <TableRow key={song.id}>
                                <TableCell className="font-medium">{song.title}</TableCell>
                                <TableCell className="text-right text-primary">${song.earnings}</TableCell>
                                <TableCell className="text-muted-foreground">Contest Q1 2024</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>
              </>
            )}

            {!isArtist && (
              <TabsContent value="votes">
                <Card className="glass border-border/50">
                  <CardHeader>
                    <CardTitle>Voting History</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Song</TableHead>
                          <TableHead>Artist</TableHead>
                          <TableHead className="text-center">Current Position</TableHead>
                          <TableHead>Voted On</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {mockVotingHistory.map((vote) => (
                          <TableRow key={vote.id}>
                            <TableCell className="font-medium">{vote.song_title}</TableCell>
                            <TableCell>{vote.artist_name}</TableCell>
                            <TableCell className="text-center">
                              <Badge variant="outline" className="text-primary border-primary/30">
                                #{vote.position}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-muted-foreground">
                              {new Date(vote.voted_at).toLocaleDateString()}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              </TabsContent>
            )}
          </Tabs>
        </motion.div>
      </main>

      <Footer />
    </div>
  );
};

export default Profile;
