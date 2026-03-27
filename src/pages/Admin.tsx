import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Users,
  Music,
  DollarSign,
  TrendingUp,
  CheckCircle,
  XCircle,
  Clock,
  BarChart3,
  Settings,
  Shield,
  Play,
  Pause,
  Eye,
  Search,
  Filter,
  Download,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Navbar } from "@/components/layout/Navbar";
import { API_ENDPOINTS, getAuthHeaders } from "@/config/api";

// Mock data for demo
const mockDashboardStats = {
  total_users: 1542,
  total_artists: 287,
  total_songs: 423,
  pending_songs: 12,
  total_votes: 45678,
  total_revenue: 7175,
  active_contest: {
    name: "Q1 2024 Music Competition",
    phase: "voting",
    days_remaining: 18,
    progress: 65,
  },
};

const mockPendingSongs = [
  {
    id: "p1",
    title: "Neon Lights",
    artist_name: "Synthwave Master",
    artist_email: "synth@example.com",
    submitted_at: "2024-03-18T10:30:00",
    file_url: "#",
    duration: "3:45",
  },
  {
    id: "p2",
    title: "Mountain Echo",
    artist_name: "Nature Sounds",
    artist_email: "nature@example.com",
    submitted_at: "2024-03-17T15:20:00",
    file_url: "#",
    duration: "4:12",
  },
  {
    id: "p3",
    title: "Urban Beat",
    artist_name: "City Producer",
    artist_email: "city@example.com",
    submitted_at: "2024-03-17T09:45:00",
    file_url: "#",
    duration: "3:28",
  },
];

const mockUsers = [
  { id: "u1", username: "musicfan123", email: "fan@example.com", role: "user", status: "active", votes_cast: 15, joined: "2024-01-10" },
  { id: "u2", username: "starproducer", email: "star@example.com", role: "artist", status: "active", songs: 5, votes_received: 342, joined: "2024-01-05" },
  { id: "u3", username: "beatmaker", email: "beat@example.com", role: "artist", status: "pending_payment", songs: 0, votes_received: 0, joined: "2024-03-15" },
  { id: "u4", username: "listener99", email: "listen@example.com", role: "user", status: "suspended", votes_cast: 3, joined: "2024-02-20" },
];

const mockContestAnalytics = {
  daily_votes: [
    { date: "Mar 12", votes: 234 },
    { date: "Mar 13", votes: 312 },
    { date: "Mar 14", votes: 287 },
    { date: "Mar 15", votes: 445 },
    { date: "Mar 16", votes: 398 },
    { date: "Mar 17", votes: 521 },
    { date: "Mar 18", votes: 367 },
  ],
  top_songs: [
    { title: "Summer Vibes", artist: "Star Producer", votes: 342 },
    { title: "Midnight Dreams", artist: "Luna Echo", votes: 298 },
    { title: "Electric Soul", artist: "Neon Pulse", votes: 276 },
  ],
  registration_trend: {
    artists_this_week: 12,
    artists_last_week: 8,
    users_this_week: 45,
    users_last_week: 38,
  },
};

const Admin = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");
  const [pendingSongs, setPendingSongs] = useState(mockPendingSongs);
  const [selectedSong, setSelectedSong] = useState<typeof mockPendingSongs[0] | null>(null);
  const [actionType, setActionType] = useState<"approve" | "reject" | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [userFilter, setUserFilter] = useState("all");

  useEffect(() => {
    // Simulate loading
    const timer = setTimeout(() => setIsLoading(false), 500);
    return () => clearTimeout(timer);
  }, []);

  const handleSongAction = async (songId: string, action: "approve" | "reject") => {
    // API call would go here
    console.log(`${action} song:`, songId, action === "reject" ? rejectionReason : "");
    
    // Remove from pending list
    setPendingSongs((prev) => prev.filter((s) => s.id !== songId));
    setSelectedSong(null);
    setActionType(null);
    setRejectionReason("");
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return <Badge className="bg-green-500/20 text-green-400 border-green-500/30">Active</Badge>;
      case "pending_payment":
        return <Badge className="bg-yellow-500/20 text-yellow-400 border-yellow-500/30">Pending Payment</Badge>;
      case "suspended":
        return <Badge className="bg-destructive/20 text-destructive border-destructive/30">Suspended</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const getRoleBadge = (role: string) => {
    switch (role) {
      case "admin":
        return <Badge className="bg-primary/20 text-primary border-primary/30">Admin</Badge>;
      case "artist":
        return <Badge className="bg-accent/20 text-accent border-accent/30">Artist</Badge>;
      default:
        return <Badge variant="outline">User</Badge>;
    }
  };

  const filteredUsers = mockUsers.filter((user) => {
    const matchesSearch =
      user.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.email.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = userFilter === "all" || user.role === userFilter || user.status === userFilter;
    return matchesSearch && matchesFilter;
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-pulse text-primary">Loading Dashboard...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <main className="container mx-auto px-4 pt-24 pb-16">
        {/* Admin Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-3xl font-bold flex items-center gap-3">
                <Shield className="h-8 w-8 text-primary" />
                Admin Dashboard
              </h1>
              <p className="text-muted-foreground mt-1">
                Manage contests, approve submissions, and monitor platform activity
              </p>
            </div>
            <Button variant="outline" onClick={() => window.location.reload()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh Data
            </Button>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <Card className="glass border-border/50">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <Users className="h-5 w-5 text-primary" />
                  <div>
                    <p className="text-2xl font-bold">{mockDashboardStats.total_users.toLocaleString()}</p>
                    <p className="text-xs text-muted-foreground">Users</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="glass border-border/50">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <Music className="h-5 w-5 text-accent" />
                  <div>
                    <p className="text-2xl font-bold">{mockDashboardStats.total_artists}</p>
                    <p className="text-xs text-muted-foreground">Artists</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="glass border-border/50">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <Play className="h-5 w-5 text-green-400" />
                  <div>
                    <p className="text-2xl font-bold">{mockDashboardStats.total_songs}</p>
                    <p className="text-xs text-muted-foreground">Songs</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="glass border-border/50">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <Clock className="h-5 w-5 text-yellow-400" />
                  <div>
                    <p className="text-2xl font-bold">{mockDashboardStats.pending_songs}</p>
                    <p className="text-xs text-muted-foreground">Pending</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="glass border-border/50">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <TrendingUp className="h-5 w-5 text-blue-400" />
                  <div>
                    <p className="text-2xl font-bold">{mockDashboardStats.total_votes.toLocaleString()}</p>
                    <p className="text-xs text-muted-foreground">Votes</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="glass border-border/50">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <DollarSign className="h-5 w-5 text-emerald-400" />
                  <div>
                    <p className="text-2xl font-bold">${mockDashboardStats.total_revenue.toLocaleString()}</p>
                    <p className="text-xs text-muted-foreground">Revenue</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </motion.div>

        {/* Contest Status Banner */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8"
        >
          <Card className="glass border-primary/30 bg-primary/5">
            <CardContent className="p-6">
              <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div>
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <BarChart3 className="h-5 w-5 text-primary" />
                    {mockDashboardStats.active_contest.name}
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Phase: <span className="text-primary capitalize">{mockDashboardStats.active_contest.phase}</span>
                    {" • "}{mockDashboardStats.active_contest.days_remaining} days remaining
                  </p>
                </div>
                <div className="flex-1 max-w-md">
                  <div className="flex justify-between text-sm mb-1">
                    <span>Contest Progress</span>
                    <span className="text-primary">{mockDashboardStats.active_contest.progress}%</span>
                  </div>
                  <Progress value={mockDashboardStats.active_contest.progress} className="h-2" />
                </div>
                <Button variant="outline">
                  <Settings className="h-4 w-4 mr-2" />
                  Manage Contest
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Main Tabs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="glass mb-6">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="approvals" className="relative">
                Song Approvals
                {pendingSongs.length > 0 && (
                  <span className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-destructive text-destructive-foreground text-xs flex items-center justify-center">
                    {pendingSongs.length}
                  </span>
                )}
              </TabsTrigger>
              <TabsTrigger value="users">User Management</TabsTrigger>
              <TabsTrigger value="analytics">Contest Analytics</TabsTrigger>
            </TabsList>

            {/* Overview Tab */}
            <TabsContent value="overview">
              <div className="grid md:grid-cols-2 gap-6">
                <Card className="glass border-border/50">
                  <CardHeader>
                    <CardTitle className="text-lg">Recent Activity</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex items-center gap-3 p-3 rounded-lg bg-secondary/50">
                        <div className="h-2 w-2 rounded-full bg-green-400" />
                        <div className="flex-1">
                          <p className="text-sm font-medium">New artist registered</p>
                          <p className="text-xs text-muted-foreground">beatmaker - 5 minutes ago</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 p-3 rounded-lg bg-secondary/50">
                        <div className="h-2 w-2 rounded-full bg-primary" />
                        <div className="flex-1">
                          <p className="text-sm font-medium">Song submitted for approval</p>
                          <p className="text-xs text-muted-foreground">Neon Lights by Synthwave Master - 10 minutes ago</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 p-3 rounded-lg bg-secondary/50">
                        <div className="h-2 w-2 rounded-full bg-yellow-400" />
                        <div className="flex-1">
                          <p className="text-sm font-medium">Payment received</p>
                          <p className="text-xs text-muted-foreground">$25.00 artist registration - 1 hour ago</p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="glass border-border/50">
                  <CardHeader>
                    <CardTitle className="text-lg">Top Performers</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {mockContestAnalytics.top_songs.map((song, i) => (
                        <div key={song.title} className="flex items-center gap-3">
                          <div className={`h-8 w-8 rounded-full flex items-center justify-center text-sm font-bold ${
                            i === 0 ? "bg-gradient-gold text-background" :
                            i === 1 ? "bg-gradient-silver text-background" :
                            "bg-gradient-bronze text-background"
                          }`}>
                            {i + 1}
                          </div>
                          <div className="flex-1">
                            <p className="font-medium">{song.title}</p>
                            <p className="text-xs text-muted-foreground">{song.artist}</p>
                          </div>
                          <Badge variant="outline" className="text-primary">{song.votes} votes</Badge>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {/* Song Approvals Tab */}
            <TabsContent value="approvals">
              <Card className="glass border-border/50">
                <CardHeader>
                  <CardTitle>Pending Song Approvals</CardTitle>
                  <CardDescription>Review and approve song submissions before they appear in the contest</CardDescription>
                </CardHeader>
                <CardContent>
                  {pendingSongs.length === 0 ? (
                    <div className="text-center py-12 text-muted-foreground">
                      <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-400" />
                      <p>All caught up! No pending submissions.</p>
                    </div>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Song</TableHead>
                          <TableHead>Artist</TableHead>
                          <TableHead>Duration</TableHead>
                          <TableHead>Submitted</TableHead>
                          <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {pendingSongs.map((song) => (
                          <TableRow key={song.id}>
                            <TableCell>
                              <div className="font-medium">{song.title}</div>
                            </TableCell>
                            <TableCell>
                              <div>{song.artist_name}</div>
                              <div className="text-xs text-muted-foreground">{song.artist_email}</div>
                            </TableCell>
                            <TableCell>{song.duration}</TableCell>
                            <TableCell className="text-muted-foreground">
                              {new Date(song.submitted_at).toLocaleDateString()}
                            </TableCell>
                            <TableCell className="text-right">
                              <div className="flex justify-end gap-2">
                                <Button size="sm" variant="outline">
                                  <Play className="h-4 w-4" />
                                </Button>
                                <Button
                                  size="sm"
                                  className="bg-green-600 hover:bg-green-700"
                                  onClick={() => {
                                    setSelectedSong(song);
                                    setActionType("approve");
                                  }}
                                >
                                  <CheckCircle className="h-4 w-4" />
                                </Button>
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  onClick={() => {
                                    setSelectedSong(song);
                                    setActionType("reject");
                                  }}
                                >
                                  <XCircle className="h-4 w-4" />
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* User Management Tab */}
            <TabsContent value="users">
              <Card className="glass border-border/50">
                <CardHeader>
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                      <CardTitle>User Management</CardTitle>
                      <CardDescription>View and manage all platform users</CardDescription>
                    </div>
                    <div className="flex gap-2">
                      <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                          placeholder="Search users..."
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          className="pl-9 w-64"
                        />
                      </div>
                      <Select value={userFilter} onValueChange={setUserFilter}>
                        <SelectTrigger className="w-40">
                          <Filter className="h-4 w-4 mr-2" />
                          <SelectValue placeholder="Filter" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Users</SelectItem>
                          <SelectItem value="user">Voters Only</SelectItem>
                          <SelectItem value="artist">Artists Only</SelectItem>
                          <SelectItem value="active">Active</SelectItem>
                          <SelectItem value="suspended">Suspended</SelectItem>
                        </SelectContent>
                      </Select>
                      <Button variant="outline">
                        <Download className="h-4 w-4 mr-2" />
                        Export
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>User</TableHead>
                        <TableHead>Role</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Activity</TableHead>
                        <TableHead>Joined</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredUsers.map((user) => (
                        <TableRow key={user.id}>
                          <TableCell>
                            <div className="font-medium">{user.username}</div>
                            <div className="text-xs text-muted-foreground">{user.email}</div>
                          </TableCell>
                          <TableCell>{getRoleBadge(user.role)}</TableCell>
                          <TableCell>{getStatusBadge(user.status)}</TableCell>
                          <TableCell className="text-muted-foreground">
                            {user.role === "artist" 
                              ? `${user.songs} songs • ${user.votes_received} votes`
                              : `${user.votes_cast} votes cast`
                            }
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {new Date(user.joined).toLocaleDateString()}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-2">
                              <Button size="sm" variant="outline">
                                <Eye className="h-4 w-4" />
                              </Button>
                              <Button size="sm" variant="outline">
                                <Settings className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Analytics Tab */}
            <TabsContent value="analytics">
              <div className="grid md:grid-cols-2 gap-6">
                <Card className="glass border-border/50">
                  <CardHeader>
                    <CardTitle>Voting Trends (Last 7 Days)</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {mockContestAnalytics.daily_votes.map((day) => (
                        <div key={day.date} className="flex items-center gap-3">
                          <span className="text-sm text-muted-foreground w-16">{day.date}</span>
                          <div className="flex-1 h-6 bg-secondary/50 rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-gradient-primary rounded-full transition-all"
                              style={{ width: `${(day.votes / 600) * 100}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium w-12 text-right">{day.votes}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card className="glass border-border/50">
                  <CardHeader>
                    <CardTitle>Registration Growth</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-4 rounded-lg bg-secondary/50">
                        <p className="text-sm text-muted-foreground">New Artists This Week</p>
                        <div className="flex items-end gap-2 mt-2">
                          <span className="text-3xl font-bold text-accent">
                            {mockContestAnalytics.registration_trend.artists_this_week}
                          </span>
                          <span className="text-sm text-green-400 mb-1">
                            +{Math.round(((mockContestAnalytics.registration_trend.artists_this_week - mockContestAnalytics.registration_trend.artists_last_week) / mockContestAnalytics.registration_trend.artists_last_week) * 100)}%
                          </span>
                        </div>
                      </div>
                      <div className="p-4 rounded-lg bg-secondary/50">
                        <p className="text-sm text-muted-foreground">New Voters This Week</p>
                        <div className="flex items-end gap-2 mt-2">
                          <span className="text-3xl font-bold text-primary">
                            {mockContestAnalytics.registration_trend.users_this_week}
                          </span>
                          <span className="text-sm text-green-400 mb-1">
                            +{Math.round(((mockContestAnalytics.registration_trend.users_this_week - mockContestAnalytics.registration_trend.users_last_week) / mockContestAnalytics.registration_trend.users_last_week) * 100)}%
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="mt-6 p-4 rounded-lg bg-primary/10 border border-primary/30">
                      <h4 className="font-medium mb-2">Revenue This Contest</h4>
                      <p className="text-2xl font-bold text-primary">${mockDashboardStats.total_revenue.toLocaleString()}</p>
                      <p className="text-sm text-muted-foreground">From {mockDashboardStats.total_artists} artist registrations</p>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </motion.div>
      </main>

      {/* Approval/Rejection Dialog */}
      <Dialog open={!!selectedSong && !!actionType} onOpenChange={() => { setSelectedSong(null); setActionType(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {actionType === "approve" ? "Approve Song" : "Reject Song"}
            </DialogTitle>
            <DialogDescription>
              {actionType === "approve"
                ? `Are you sure you want to approve "${selectedSong?.title}" by ${selectedSong?.artist_name}?`
                : `Please provide a reason for rejecting "${selectedSong?.title}".`
              }
            </DialogDescription>
          </DialogHeader>
          
          {actionType === "reject" && (
            <Textarea
              placeholder="Enter rejection reason..."
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              className="min-h-24"
            />
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => { setSelectedSong(null); setActionType(null); }}>
              Cancel
            </Button>
            <Button
              variant={actionType === "approve" ? "default" : "destructive"}
              onClick={() => selectedSong && handleSongAction(selectedSong.id, actionType!)}
              disabled={actionType === "reject" && !rejectionReason.trim()}
            >
              {actionType === "approve" ? "Approve Song" : "Reject Song"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Admin;
