import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Users,
  Music,
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
  Loader2,
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
import { API_ENDPOINTS, APP_CONFIG, getAuthHeaders } from "@/config/api";
import { useAuth } from "@/contexts/AuthContext";

interface PendingSong {
  id: number;
  title: string;
  audio_url: string;
  cover_image: string | null;
  duration: number | null;
  vote_count: number;
  status: string;
  created_at: string | null;
  artist?: {
    id: number;
    stage_name: string;
    profile_image: string | null;
  } | null;
}

interface AdminUser {
  id: number;
  name: string;
  username: string;
  email: string;
  roles: string[];
  status: string;
  is_active: boolean;
  songs_count: number;
  votes_received: number;
  votes_cast: number;
  created_at: string | null;
  artist_profile?: {
    id: number;
    stage_name: string;
    bio?: string | null;
    genre?: string | null;
    profile_image?: string | null;
    is_paid?: boolean;
    is_verified?: boolean;
  } | null;
}

interface AdminPayment {
  id: number;
  user_id: number;
  contest_id: number | null;
  transaction_id: string;
  tx_ref: string;
  amount: number;
  currency: string;
  status: "pending" | "successful" | "reversed" | string;
  payment_type: string | null;
  payment_purpose: string;
  created_at: string | null;
  verified_at: string | null;
  contest_title: string | null;
  user: {
    id: number;
    name: string;
    username: string;
    email: string;
  } | null;
}

interface DashboardStats {
  total_users: number;
  total_artists: number;
  total_songs: number;
  pending_songs: number;
  total_votes: number;
  total_revenue: number;
}

interface DashboardData {
  stats: DashboardStats;
  current_contest: {
    id: number;
    title: string;
    phase: string;
    start_date: string;
    submission_end_date: string;
    voting_end_date: string;
  } | null;
  recent_activity: Array<{
    timestamp: string | null;
    type: "user" | "song" | "payment";
    title: string;
    detail: string;
  }>;
}

interface AnalyticsData {
  daily_votes: Array<{ date: string; label: string; votes: number }>;
  top_songs: Array<{ title: string; artist: string; votes: number }>;
  registration_trend: {
    artists_this_week: number;
    artists_last_week: number;
    users_this_week: number;
    users_last_week: number;
  };
  contest_revenue: number;
  contest_title: string | null;
}

const getMediaUrl = (url: string | null | undefined) => {
  if (!url) return null;
  return new URL(url, new URL(API_ENDPOINTS.SONGS.BASE).origin).toString();
};

const formatNaira = (amount: number) =>
  `${APP_CONFIG.CURRENCY_SYMBOL}${amount.toLocaleString("en-NG", { maximumFractionDigits: 2 })}`;

const formatDuration = (duration: number | null) => {
  if (duration === null) return "Duration unavailable";
  const minutes = Math.floor(duration / 60);
  const seconds = duration % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
};

const toDateTimeLocal = (value: string) => {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "";
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 16);
};

type UserExportFormat = "pdf" | "csv" | "xml" | "excel" | "jpeg";
type UserExportRow = Record<string, string>;

const getUserRole = (user: AdminUser) =>
  user.roles.includes("admin") ? "admin" : user.roles.includes("artist") ? "artist" : "voter";

const makeUserExportRows = (users: AdminUser[]): UserExportRow[] =>
  users.map((user) => ({
    Name: user.name || user.username,
    Username: user.username,
    Email: user.email,
    Role: getUserRole(user),
    "Account Status": user.is_active ? "Active" : "Deactivated",
    "Season Status": user.status.replaceAll("_", " "),
    Activity: user.roles.includes("artist")
      ? `${user.songs_count} songs, ${user.votes_received} votes received`
      : `${user.votes_cast} votes cast`,
    Joined: user.created_at ? new Date(user.created_at).toLocaleDateString() : "",
  }));

const escapeXml = (value: string) =>
  value.replace(/[<>&'"]/g, (character) => ({
    "<": "&lt;",
    ">": "&gt;",
    "&": "&amp;",
    "'": "&apos;",
    '"': "&quot;",
  })[character] || character);

const downloadBlob = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
};

const exportUsersAsJpeg = async (rows: UserExportRow[], filename: string) => {
  const headers = Object.keys(rows[0] || {
    Name: "",
    Username: "",
    Email: "",
    Role: "",
    "Account Status": "",
    "Season Status": "",
    Activity: "",
    Joined: "",
  });
  const rowHeight = 42;
  const canvas = document.createElement("canvas");
  canvas.width = 1800;
  canvas.height = Math.max(180, 120 + (rows.length + 1) * rowHeight);
  const context = canvas.getContext("2d");
  if (!context) throw new Error("Could not create an image for export.");

  context.fillStyle = "#ffffff";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "#111827";
  context.font = "bold 32px Arial";
  context.fillText("Soundwar User Management", 40, 48);
  context.fillStyle = "#6b7280";
  context.font = "18px Arial";
  context.fillText(`Exported ${new Date().toLocaleString()} · ${rows.length} users`, 40, 80);

  const tableTop = 110;
  const colWidth = (canvas.width - 80) / headers.length;
  context.fillStyle = "#e5e7eb";
  context.fillRect(40, tableTop, canvas.width - 80, rowHeight);
  context.font = "bold 16px Arial";
  context.fillStyle = "#111827";
  headers.forEach((header, index) => {
    context.fillText(header, 50 + index * colWidth, tableTop + 26, colWidth - 18);
  });

  context.font = "15px Arial";
  rows.forEach((row, rowIndex) => {
    const y = tableTop + (rowIndex + 1) * rowHeight;
    if (rowIndex % 2 === 1) {
      context.fillStyle = "#f9fafb";
      context.fillRect(40, y, canvas.width - 80, rowHeight);
    }
    context.fillStyle = "#1f2937";
    headers.forEach((header, columnIndex) => {
      context.fillText(row[header] || "", 50 + columnIndex * colWidth, y + 26, colWidth - 18);
    });
    context.strokeStyle = "#e5e7eb";
    context.beginPath();
    context.moveTo(40, y + rowHeight);
    context.lineTo(canvas.width - 40, y + rowHeight);
    context.stroke();
  });

  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((result) => {
      if (result) resolve(result);
      else reject(new Error("Could not encode the user list as JPEG."));
    }, "image/jpeg", 0.92);
  });
  downloadBlob(blob, filename);
};

const Admin = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("overview");
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [payments, setPayments] = useState<AdminPayment[]>([]);
  const [isLoadingData, setIsLoadingData] = useState(true);
  const [dataError, setDataError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [pendingSongs, setPendingSongs] = useState<PendingSong[]>([]);
  const [isLoadingPendingSongs, setIsLoadingPendingSongs] = useState(true);
  const [pendingSongsError, setPendingSongsError] = useState("");
  const [pendingSongsRefreshKey, setPendingSongsRefreshKey] = useState(0);
  const [selectedSong, setSelectedSong] = useState<PendingSong | null>(null);
  const [actionType, setActionType] = useState<"approve" | "reject" | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const [isSongActionLoading, setIsSongActionLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [userFilter, setUserFilter] = useState("all");
  const [paymentFilter, setPaymentFilter] = useState("all");
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);
  const [selectedPayment, setSelectedPayment] = useState<AdminPayment | null>(null);
  const [paymentStatus, setPaymentStatus] = useState<AdminPayment["status"]>("pending");
  const [isUpdatingUserStatus, setIsUpdatingUserStatus] = useState(false);
  const [isUpdatingPaymentStatus, setIsUpdatingPaymentStatus] = useState(false);
  const [isTriggeringReminder, setIsTriggeringReminder] = useState(false);
  const [isUpdatingContestPhase, setIsUpdatingContestPhase] = useState(false);
  const [isEditingSeasonDates, setIsEditingSeasonDates] = useState(false);
  const [isCreatingNewSeason, setIsCreatingNewSeason] = useState(false);
  const [isSavingSeasonDates, setIsSavingSeasonDates] = useState(false);
  const [seasonDateForm, setSeasonDateForm] = useState({
    start_date: "",
    submission_end_date: "",
    voting_end_date: "",
  });
  const { toast } = useToast();
  const { token, user, isLoading: isAuthLoading } = useAuth();
  const isAdmin = Boolean(user?.roles?.includes("admin"));

  useEffect(() => {
    if (!token || !isAdmin) return;
    const controller = new AbortController();

    const loadAdminData = async () => {
      setIsLoadingData(true);
      setDataError("");
      const fetchData = async <T,>(url: string) => {
        try {
          const response = await fetch(url, {
            headers: getAuthHeaders(token),
            signal: controller.signal,
          });
          const data = await response.json().catch(() => ({}));
          if (!response.ok) {
            throw new Error(data.error || `Request failed (${response.status}).`);
          }
          return { data: data as T, error: "" };
        } catch (error) {
          return {
            data: null,
            error: error instanceof Error ? error.message : "Request failed.",
          };
        }
      };

      const [dashboardResult, usersResult, analyticsResult, paymentsResult] = await Promise.all([
        fetchData<DashboardData>(API_ENDPOINTS.ADMIN.DASHBOARD),
        fetchData<{ users: AdminUser[] }>(API_ENDPOINTS.ADMIN.USERS),
        fetchData<AnalyticsData>(API_ENDPOINTS.ADMIN.ANALYTICS),
        fetchData<{ payments: AdminPayment[] }>(API_ENDPOINTS.ADMIN.PAYMENTS),
      ]);

      if (controller.signal.aborted) return;
      if (dashboardResult.data) setDashboard(dashboardResult.data);
      if (usersResult.data) setUsers(usersResult.data.users || []);
      if (analyticsResult.data) setAnalytics(analyticsResult.data);
      if (paymentsResult.data) setPayments(paymentsResult.data.payments || []);

      const failures = [
        dashboardResult.error && `Dashboard: ${dashboardResult.error}`,
        usersResult.error && `Users: ${usersResult.error}`,
        analyticsResult.error && `Analytics: ${analyticsResult.error}`,
        paymentsResult.error && `Payments: ${paymentsResult.error}`,
      ].filter(Boolean);
      setDataError(failures.length ? `Some dashboard data could not be loaded. ${failures.join(" ")}` : "");
      setIsLoadingData(false);
    };

    void loadAdminData();
    return () => controller.abort();
  }, [token, isAdmin, refreshKey]);

  useEffect(() => {
    if (!isAuthLoading && !isAdmin) {
      navigate("/admin/login", { replace: true });
    }
  }, [isAuthLoading, isAdmin, navigate]);

  useEffect(() => {
    const controller = new AbortController();

    const loadPendingSongs = async () => {
      setIsLoadingPendingSongs(true);
      setPendingSongsError("");

      if (!token) {
        setPendingSongsError("Sign in with an administrator account to review submissions.");
        setIsLoadingPendingSongs(false);
        return;
      }

      try {
        const response = await fetch(API_ENDPOINTS.ADMIN.PENDING_SONGS, {
          headers: getAuthHeaders(token),
          signal: controller.signal,
        });
        const data = await response.json() as { songs?: PendingSong[]; error?: string };

        if (!response.ok) {
          throw new Error(data.error || "Could not load pending submissions.");
        }

        setPendingSongs(data.songs || []);
      } catch (error) {
        if (!controller.signal.aborted) {
          setPendingSongsError(error instanceof Error ? error.message : "Could not load pending submissions.");
        }
      } finally {
        if (!controller.signal.aborted) setIsLoadingPendingSongs(false);
      }
    };

    void loadPendingSongs();
    return () => controller.abort();
  }, [token, pendingSongsRefreshKey]);

  const handleSongAction = async (songId: string, action: "approve" | "reject") => {
    if (!token) return;

    setIsSongActionLoading(true);
    try {
      const response = await fetch(
        action === "approve"
          ? API_ENDPOINTS.ADMIN.APPROVE(songId)
          : API_ENDPOINTS.ADMIN.REJECT(songId),
        {
          method: "POST",
          headers: getAuthHeaders(token),
          ...(action === "reject" && { body: JSON.stringify({ reason: rejectionReason.trim() }) }),
        },
      );
      const contentType = response.headers.get("content-type") || "";
      const data = contentType.includes("application/json")
        ? await response.json() as { error?: string }
        : { error: `Server returned ${response.status} without a JSON response.` };

      if (!response.ok) {
        throw new Error(data.error || `Could not ${action} this song.`);
      }

      setPendingSongs((currentSongs) => currentSongs.filter((song) => String(song.id) !== songId));
      setRefreshKey((key) => key + 1);
      setSelectedSong(null);
      setActionType(null);
      setRejectionReason("");
      toast({
        title: action === "approve" ? "Song approved" : "Song rejected",
        description: action === "approve"
          ? "The track is now approved for the contest."
          : "The track has been rejected with your feedback.",
      });
    } catch (error) {
      toast({
        title: `Could not ${action} song`,
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSongActionLoading(false);
    }
  };

  const handleTriggerReparticipation = async () => {
    setIsTriggeringReminder(true);

    try {
      const token = localStorage.getItem("auth_token");
      const response = await fetch(API_ENDPOINTS.ADMIN.REPARTICIPATION, {
        method: "POST",
        headers: getAuthHeaders(token || undefined),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || data.message || "Failed to trigger notifications.");
      }

      toast({
        title: "Winner reminder sent",
        description: `${data.notifications_sent || 0} past winner(s) notified.`,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not trigger reminder.";
      toast({
        title: "Reminder failed",
        description: message,
        variant: "destructive",
      });
    } finally {
      setIsTriggeringReminder(false);
    }
  };

  const handleUserStatusChange = async (targetUser: AdminUser) => {
    if (!token) return;

    const is_active = !targetUser.is_active;
    setIsUpdatingUserStatus(true);
    try {
      const response = await fetch(API_ENDPOINTS.ADMIN.USER_STATUS(targetUser.id), {
        method: "PUT",
        headers: getAuthHeaders(token),
        body: JSON.stringify({ is_active }),
      });
      const data = await response.json().catch(() => ({})) as { error?: string };
      if (!response.ok) {
        throw new Error(data.error || "Could not update this account.");
      }

      setUsers((currentUsers) => currentUsers.map((currentUser) =>
        currentUser.id === targetUser.id ? { ...currentUser, is_active } : currentUser,
      ));
      setSelectedUser((currentUser) =>
        currentUser?.id === targetUser.id ? { ...currentUser, is_active } : currentUser,
      );
      toast({
        title: is_active ? "Account activated" : "Account deactivated",
        description: `${targetUser.name || targetUser.username}'s account is now ${is_active ? "active" : "inactive"}.`,
      });
    } catch (error) {
      toast({
        title: "Could not update account",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsUpdatingUserStatus(false);
    }
  };

  const handlePaymentStatusChange = async () => {
    if (!token || !selectedPayment) return;

    setIsUpdatingPaymentStatus(true);
    try {
      const response = await fetch(API_ENDPOINTS.ADMIN.PAYMENT_STATUS(selectedPayment.id), {
        method: "PUT",
        headers: getAuthHeaders(token),
        body: JSON.stringify({ status: paymentStatus }),
      });
      const data = await response.json().catch(() => ({})) as {
        error?: string;
        payment?: AdminPayment;
      };
      if (!response.ok) {
        throw new Error(data.error || "Could not update this payment.");
      }

      if (!data.payment) {
        throw new Error("Server response did not include the updated payment.");
      }
      const updatedPayment = data.payment;
      setPayments((currentPayments) => currentPayments.map((payment) =>
        payment.id === updatedPayment.id ? updatedPayment : payment,
      ));
      setRefreshKey((key) => key + 1);
      toast({
        title: "Payment status updated",
        description: `Payment #${selectedPayment.id} is now ${paymentStatus}.`,
      });
      setSelectedPayment(null);
    } catch (error) {
      toast({
        title: "Could not update payment",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsUpdatingPaymentStatus(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return <Badge className="bg-green-500/20 text-green-400 border-green-500/30">Active</Badge>;
      case "pending_payment":
        return <Badge className="bg-yellow-500/20 text-yellow-400 border-yellow-500/30">Pending Payment</Badge>;
      case "not_entered":
        return <Badge variant="outline">Not entered this season</Badge>;
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

  const filteredUsers = users.filter((user) => {
    const roles = user.roles || [];
    const role = roles.includes("admin") ? "admin" : roles.includes("artist") ? "artist" : "user";
    const matchesSearch =
      user.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = userFilter === "all"
      || role === userFilter
      || (userFilter === "active" && user.is_active);
    return matchesSearch && matchesFilter;
  });
  const filteredPayments = payments.filter((payment) =>
    paymentFilter === "all" || payment.status === paymentFilter,
  );

  const exportUsers = async (format: UserExportFormat) => {
    const rows = makeUserExportRows(filteredUsers);
    const timestamp = new Date().toISOString().slice(0, 10);
    const baseFilename = `soundwar-users-${timestamp}`;
    const headers = Object.keys(rows[0] || {
      Name: "",
      Username: "",
      Email: "",
      Role: "",
      "Account Status": "",
      "Season Status": "",
      Activity: "",
      Joined: "",
    });

    try {
      if (format === "csv") {
        const csv = [
          headers.join(","),
          ...rows.map((row) => headers.map((header) => {
            const value = row[header] || "";
            const safeValue = /^\s*[=+\-@]/.test(value) ? `'${value}` : value;
            return `"${safeValue.replaceAll('"', '""')}"`;
          }).join(",")),
        ].join("\r\n");
        downloadBlob(new Blob(["\uFEFF", csv], { type: "text/csv;charset=utf-8" }), `${baseFilename}.csv`);
      } else if (format === "xml") {
        const xmlRows = rows.map((row) =>
          `  <user>\n${headers.map((header) =>
            `    <${header.replaceAll(" ", "")}>${escapeXml(row[header] || "")}</${header.replaceAll(" ", "")}>`,
          ).join("\n")}\n  </user>`,
        );
        const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<users>\n${xmlRows.join("\n")}\n</users>`;
        downloadBlob(new Blob([xml], { type: "application/xml;charset=utf-8" }), `${baseFilename}.xml`);
      } else if (format === "excel") {
        const workbookRows = [
          `<Row>${headers.map((header) => `<Cell><Data ss:Type="String">${escapeXml(header)}</Data></Cell>`).join("")}</Row>`,
          ...rows.map((row) =>
            `<Row>${headers.map((header) => `<Cell><Data ss:Type="String">${escapeXml(row[header] || "")}</Data></Cell>`).join("")}</Row>`,
          ),
        ];
        const workbook = `<?xml version="1.0"?><?mso-application progid="Excel.Sheet"?>\n<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="Users"><Table>${workbookRows.join("")}</Table></Worksheet></Workbook>`;
        downloadBlob(new Blob([workbook], { type: "application/vnd.ms-excel;charset=utf-8" }), `${baseFilename}.xls`);
      } else if (format === "jpeg") {
        await exportUsersAsJpeg(rows, `${baseFilename}.jpg`);
      } else {
        const { jsPDF } = await import("jspdf");
        const document = new jsPDF({ orientation: "landscape", unit: "pt", format: "a4" });
        const pageWidth = document.internal.pageSize.getWidth();
        const pageHeight = document.internal.pageSize.getHeight();
        const columnWidths = [95, 80, 150, 50, 75, 90, 135, 65];
        const startX = 28;
        const tableWidth = columnWidths.reduce((sum, width) => sum + width, 0);
        const scale = Math.min(1, (pageWidth - startX * 2) / tableWidth);
        const widths = columnWidths.map((width) => width * scale);
        const rowHeight = 24;
        let y = 58;

        const drawHeader = () => {
          document.setFillColor(229, 231, 235);
          document.rect(startX, y - 15, pageWidth - startX * 2, rowHeight, "F");
          document.setFont("helvetica", "bold");
          document.setFontSize(7);
          let x = startX + 5;
          headers.forEach((header, index) => {
            document.text(header, x, y, { maxWidth: widths[index] - 8 });
            x += widths[index];
          });
          y += rowHeight;
          document.setFont("helvetica", "normal");
        };

        document.setFont("helvetica", "bold");
        document.setFontSize(15);
        document.text("Soundwar User Management", startX, 28);
        document.setFont("helvetica", "normal");
        document.setFontSize(8);
        document.text(`Exported ${new Date().toLocaleString()} | ${rows.length} users`, startX, 42);
        drawHeader();

        rows.forEach((row, rowIndex) => {
          if (y + rowHeight > pageHeight - 24) {
            document.addPage();
            y = 40;
            drawHeader();
          }
          if (rowIndex % 2 === 1) {
            document.setFillColor(249, 250, 251);
            document.rect(startX, y - 15, pageWidth - startX * 2, rowHeight, "F");
          }
          document.setFontSize(7);
          let x = startX + 5;
          headers.forEach((header, index) => {
            const value = row[header] || "";
            const maxCharacters = Math.max(5, Math.floor((widths[index] - 8) / 3.6));
            const clippedValue = value.length > maxCharacters
              ? `${value.slice(0, maxCharacters - 3)}...`
              : value;
            document.text(clippedValue, x, y, { maxWidth: widths[index] - 8 });
            x += widths[index];
          });
          y += rowHeight;
        });

        downloadBlob(document.output("blob"), `${baseFilename}.pdf`);
      }
      toast({ title: "User list exported", description: `Downloaded ${baseFilename}.${format === "excel" ? "xls" : format === "jpeg" ? "jpg" : format}.` });
    } catch (error) {
      toast({
        title: "Could not export users",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    }
  };

  const contest = dashboard?.current_contest;
  const contestStart = contest ? new Date(contest.start_date).getTime() : 0;
  const submissionEnd = contest ? new Date(contest.submission_end_date).getTime() : 0;
  const votingEnd = contest ? new Date(contest.voting_end_date).getTime() : 0;
  const hasValidContestDates = Boolean(
    contest &&
    Number.isFinite(contestStart) &&
    Number.isFinite(submissionEnd) &&
    Number.isFinite(votingEnd) &&
    contestStart < submissionEnd &&
    submissionEnd < votingEnd,
  );
  const phaseDeadline = !hasValidContestDates ? 0 : contest?.phase === "upcoming"
    ? contestStart
    : contest?.phase === "submission"
      ? submissionEnd
      : contest?.phase === "voting"
        ? votingEnd
        : 0;
  const daysRemaining = phaseDeadline > Date.now()
    ? Math.ceil((phaseDeadline - Date.now()) / (1000 * 60 * 60 * 24))
    : 0;
  const contestProgress = contest && hasValidContestDates
    ? Math.min(100, Math.max(0, ((Date.now() - contestStart) / (votingEnd - contestStart)) * 100))
    : 0;
  const formatContestDate = (value: string | undefined) => {
    if (!value || !Number.isFinite(new Date(value).getTime())) return "Date unavailable";
    return new Date(value).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  };
  const maximumDailyVotes = Math.max(1, ...(analytics?.daily_votes.map((day) => day.votes) || [0]));

  const percentageChange = (current: number, previous: number) => {
    if (previous === 0) return current === 0 ? "0%" : "New";
    const change = Math.round(((current - previous) / previous) * 100);
    return `${change > 0 ? "+" : ""}${change}%`;
  };

  const advanceContestPhase = async (phase: "voting" | "completed") => {
    if (!contest || !token) return;

    setIsUpdatingContestPhase(true);
    try {
      const response = await fetch(API_ENDPOINTS.ADMIN.CONTEST_PHASE(contest.id), {
        method: "POST",
        headers: getAuthHeaders(token),
        body: JSON.stringify({ phase }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || "Could not update the contest phase.");
      }

      toast({
        title: phase === "voting" ? "Voting is open" : "Season completed",
        description: `${data.contest.title} is now in the ${phase} phase.`,
      });
      setRefreshKey((key) => key + 1);
    } catch (error) {
      toast({
        title: "Could not update contest phase",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsUpdatingContestPhase(false);
    }
  };

  const openSeasonDateEditor = () => {
    if (!contest) return;
    setSeasonDateForm({
      start_date: toDateTimeLocal(contest.start_date),
      submission_end_date: toDateTimeLocal(contest.submission_end_date),
      voting_end_date: toDateTimeLocal(contest.voting_end_date),
    });
    setIsCreatingNewSeason(false);
    setIsEditingSeasonDates(true);
  };

  const openSeasonCreationDialog = () => {
    setSeasonDateForm({
      start_date: "",
      submission_end_date: "",
      voting_end_date: "",
    });
    setIsEditingSeasonDates(false);
    setIsCreatingNewSeason(true);
  };

  const saveNewSeason = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token) return;

    const { start_date, submission_end_date, voting_end_date } = seasonDateForm;
    if (!start_date || !submission_end_date || !voting_end_date || !(start_date < submission_end_date && submission_end_date < voting_end_date)) {
      toast({
        title: "Invalid season schedule",
        description: "Set the season start before submission closes, and submission close before voting ends.",
        variant: "destructive",
      });
      return;
    }

    setIsSavingSeasonDates(true);
    try {
      const response = await fetch(API_ENDPOINTS.ADMIN.CONTESTS, {
        method: "POST",
        headers: getAuthHeaders(token),
        body: JSON.stringify({
          start_date: `${start_date}:00`,
          submission_end_date: `${submission_end_date}:00`,
          voting_end_date: `${voting_end_date}:00`,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || "Could not create a new season.");
      }
      if (!data.contest?.title) {
        throw new Error("Server response did not include the new season details.");
      }

      toast({
        title: "New season created",
        description: `${data.contest.title} is now the active season.`,
      });
      setIsCreatingNewSeason(false);
      setRefreshKey((key) => key + 1);
    } catch (error) {
      toast({
        title: "Could not create new season",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSavingSeasonDates(false);
    }
  };

  const saveSeasonDates = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!contest || !token) return;

    const { start_date, submission_end_date, voting_end_date } = seasonDateForm;
    if (!start_date || !submission_end_date || !voting_end_date || !(start_date < submission_end_date && submission_end_date < voting_end_date)) {
      toast({
        title: "Invalid season schedule",
        description: "Set the season start before submission closes, and submission close before voting ends.",
        variant: "destructive",
      });
      return;
    }

    setIsSavingSeasonDates(true);
    try {
      const response = await fetch(API_ENDPOINTS.ADMIN.CONTEST_DATES(contest.id), {
        method: "PUT",
        headers: getAuthHeaders(token),
        body: JSON.stringify({
          start_date: `${start_date}:00`,
          submission_end_date: `${submission_end_date}:00`,
          voting_end_date: `${voting_end_date}:00`,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || "Could not update season dates.");
      }

      toast({ title: "Season dates updated", description: `${data.contest.title} schedule has been saved.` });
      setIsEditingSeasonDates(false);
      setRefreshKey((key) => key + 1);
    } catch (error) {
      toast({
        title: "Could not update season dates",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSavingSeasonDates(false);
    }
  };

  if (isAuthLoading || !isAdmin) {
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
<div className="flex flex-col gap-3 md:flex-row items-start md:items-center justify-between mb-6">
              <div>
                <h1 className="text-3xl font-bold flex items-center gap-3">
                  <Shield className="h-8 w-8 text-primary" />
                  Admin Dashboard
                </h1>
                <p className="text-muted-foreground mt-1">
                  Manage contests, approve submissions, and monitor platform activity
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <Button variant="outline" onClick={() => setRefreshKey((key) => key + 1)} disabled={isLoadingData}>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  {isLoadingData ? "Refreshing..." : "Refresh Data"}
                </Button>
                <Button
                  variant="secondary"
                  onClick={handleTriggerReparticipation}
                  disabled={isTriggeringReminder}
                >
                  <Clock className="h-4 w-4 mr-2" />
                  {isTriggeringReminder ? "Sending reminder..." : "Trigger Winner Reminder"}
                </Button>
              </div>
          </div>

          {dataError && (
            <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3" role="alert">
              <p className="text-sm text-destructive">{dataError}</p>
              <Button variant="outline" size="sm" onClick={() => setRefreshKey((key) => key + 1)}>
                <RefreshCw className="h-4 w-4 mr-2" />Retry
              </Button>
            </div>
          )}

          {/* Quick Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <Card className="glass border-border/50">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <Users className="h-5 w-5 text-primary" />
                  <div>
                    <p className="text-2xl font-bold">{dashboard?.stats.total_users.toLocaleString() ?? "—"}</p>
                    <p className="text-xs text-muted-foreground">All Users</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="glass border-border/50">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <Music className="h-5 w-5 text-accent" />
                  <div>
                    <p className="text-2xl font-bold">{dashboard?.stats.total_artists.toLocaleString() ?? "—"}</p>
                    <p className="text-xs text-muted-foreground">Artists this season</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="glass border-border/50">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <Play className="h-5 w-5 text-green-400" />
                  <div>
                    <p className="text-2xl font-bold">{dashboard?.stats.total_songs.toLocaleString() ?? "—"}</p>
                    <p className="text-xs text-muted-foreground">Songs this season</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="glass border-border/50">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <Clock className="h-5 w-5 text-yellow-400" />
                  <div>
                    <p className="text-2xl font-bold">{dashboard?.stats.pending_songs.toLocaleString() ?? "—"}</p>
                    <p className="text-xs text-muted-foreground">Pending this season</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="glass border-border/50">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <TrendingUp className="h-5 w-5 text-blue-400" />
                  <div>
                    <p className="text-2xl font-bold">{dashboard?.stats.total_votes.toLocaleString() ?? "—"}</p>
                    <p className="text-xs text-muted-foreground">Votes this season</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="glass border-border/50">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <span className="flex h-5 w-5 items-center justify-center font-semibold text-emerald-400">₦</span>
                  <div>
                    <p className="text-2xl font-bold">{dashboard ? formatNaira(dashboard.stats.total_revenue) : "—"}</p>
                    <p className="text-xs text-muted-foreground">Revenue this season</p>
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
            <CardHeader>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5 text-primary" />
                    {contest?.title || "No active contest season"}
                  </CardTitle>
                  {contest && (
                    <CardDescription className="mt-2">
                      Active season #{contest.id} · Phase: <span className="capitalize text-primary">{contest.phase}</span>
                      {phaseDeadline > 0 && <> · {daysRemaining} days remaining</>}
                    </CardDescription>
                  )}
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {(!contest || contest.phase === "completed") && (
                    <Button onClick={openSeasonCreationDialog}>
                      <CalendarClock className="mr-2 h-4 w-4" />
                      Create New Season
                    </Button>
                  )}
                  {contest && (
                    <Button variant="outline" onClick={openSeasonDateEditor}>
                      <CalendarClock className="mr-2 h-4 w-4" />Edit dates
                    </Button>
                  )}
                  {contest && hasValidContestDates && (
                    <Badge variant="outline">{Math.round(contestProgress)}% complete</Badge>
                  )}
                  {contest?.phase === "submission" && (
                    <Button onClick={() => advanceContestPhase("voting")} disabled={isUpdatingContestPhase}>
                      {isUpdatingContestPhase ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
                      Start voting
                    </Button>
                  )}
                  {contest?.phase === "voting" && (
                    <Button variant="outline" onClick={() => advanceContestPhase("completed")} disabled={isUpdatingContestPhase}>
                      {isUpdatingContestPhase ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle className="mr-2 h-4 w-4" />}
                      Complete season
                    </Button>
                  )}
                  {contest?.phase === "completed" && <Badge variant="secondary">Season completed</Badge>}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-5">
              {contest ? (
                <>
                  <div className="grid gap-4 border-y border-border/60 py-4 sm:grid-cols-3">
                    <div>
                      <p className="text-xs uppercase text-muted-foreground">Season starts</p>
                      <p className="mt-1 text-sm font-medium">{formatContestDate(contest.start_date)}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase text-muted-foreground">Submission closes</p>
                      <p className="mt-1 text-sm font-medium">{formatContestDate(contest.submission_end_date)}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase text-muted-foreground">Voting ends</p>
                      <p className="mt-1 text-sm font-medium">{formatContestDate(contest.voting_end_date)}</p>
                    </div>
                  </div>
                  {!hasValidContestDates ? (
                    <div className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm" role="alert">
                      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
                      <p className="text-destructive">
                        This season’s dates are out of order. Set the start date before submission closes, and set submission close before voting ends. Progress and deadline countdown are hidden until corrected.
                      </p>
                    </div>
                  ) : (
                    <Progress value={contestProgress} className="h-2" aria-label="Contest season progress" />
                  )}
                </>
              ) : (
                <p className="text-sm text-muted-foreground">Season-specific counts are zero until a contest is activated.</p>
              )}
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
            <TabsList className="glass mb-6 w-full justify-start overflow-x-auto">
              <TabsTrigger value="overview" className="shrink-0">Overview</TabsTrigger>
              <TabsTrigger value="approvals" className="relative shrink-0">
                Song Approvals
                {pendingSongs.length > 0 && (
                  <span className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-destructive text-destructive-foreground text-xs flex items-center justify-center">
                    {pendingSongs.length}
                  </span>
                )}
              </TabsTrigger>
              <TabsTrigger value="users" className="shrink-0">User Management</TabsTrigger>
              <TabsTrigger value="analytics" className="shrink-0">Contest Analytics</TabsTrigger>
            </TabsList>

            {/* Overview Tab */}
            <TabsContent value="overview">
              <div className="grid md:grid-cols-2 gap-6">
                <Card className="glass border-border/50">
                  <CardHeader>
                    <CardTitle className="text-lg">Recent Activity</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {isLoadingData ? (
                      <p className="py-8 text-center text-sm text-muted-foreground" role="status">Loading activity...</p>
                    ) : dashboard?.recent_activity.length ? (
                      <div className="space-y-4">
                        {dashboard.recent_activity.map((activity, index) => (
                          <div key={`${activity.type}-${activity.timestamp}-${index}`} className="flex items-center gap-3 p-3 rounded-lg bg-secondary/50">
                            <div className={`h-2 w-2 rounded-full ${activity.type === "payment" ? "bg-yellow-400" : activity.type === "song" ? "bg-primary" : "bg-green-400"}`} />
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium">{activity.title}</p>
                              <p className="text-xs text-muted-foreground truncate">
                                {activity.detail}{activity.timestamp ? ` · ${new Date(activity.timestamp).toLocaleString()}` : ""}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="py-8 text-center text-sm text-muted-foreground">No activity recorded yet.</p>
                    )}
                  </CardContent>
                </Card>

                <Card className="glass border-border/50">
                  <CardHeader>
                    <CardTitle className="text-lg">Top Performers</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {isLoadingData ? (
                      <p className="py-8 text-center text-sm text-muted-foreground" role="status">Loading performers...</p>
                    ) : analytics?.top_songs.length ? (
                    <div className="space-y-4">
                      {analytics.top_songs.map((song, i) => (
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
                    ) : (
                      <p className="py-8 text-center text-sm text-muted-foreground">No approved songs to rank yet.</p>
                    )}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {/* Song Approvals Tab */}
            <TabsContent value="approvals">
              <Card className="glass border-border/50">
                <CardHeader>
                  <CardTitle>Pending Song Approvals · {contest?.title || "No active season"}</CardTitle>
                  <CardDescription>Review pending submissions for the active contest season.</CardDescription>
                </CardHeader>
                <CardContent>
                  {isLoadingPendingSongs ? (
                    <div className="flex items-center justify-center gap-2 py-12 text-muted-foreground" role="status">
                      <Loader2 className="h-5 w-5 animate-spin" />
                      Loading pending submissions...
                    </div>
                  ) : pendingSongsError ? (
                    <div className="text-center py-12" role="alert">
                      <p className="text-sm text-destructive">{pendingSongsError}</p>
                      <Button
                        variant="outline"
                        className="mt-4"
                        onClick={() => setPendingSongsRefreshKey((key) => key + 1)}
                      >
                        <RefreshCw className="h-4 w-4 mr-2" />
                        Retry
                      </Button>
                    </div>
                  ) : pendingSongs.length === 0 ? (
                    <div className="text-center py-12 text-muted-foreground">
                      <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-400" />
                      <p className="font-medium text-foreground">All caught up</p>
                      <p className="text-sm mt-1">There are no pending song submissions to review.</p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                    <Table className="min-w-[850px]">
                      <TableHeader>
                        <TableRow>
                          <TableHead>Song</TableHead>
                          <TableHead>Artist</TableHead>
                          <TableHead>Votes</TableHead>
                          <TableHead>Duration</TableHead>
                          <TableHead>Submitted</TableHead>
                          <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {pendingSongs.map((song) => (
                          <TableRow key={song.id}>
                            <TableCell className="min-w-[250px]">
                              <div className="flex items-center gap-3">
                                {getMediaUrl(song.cover_image || song.artist?.profile_image) ? (
                                  <img
                                    src={getMediaUrl(song.cover_image || song.artist?.profile_image) || undefined}
                                    alt=""
                                    className="h-11 w-11 rounded-md object-cover"
                                  />
                                ) : (
                                  <div className="h-11 w-11 rounded-md bg-primary/10 flex items-center justify-center">
                                    <Music className="h-5 w-5 text-primary" />
                                  </div>
                                )}
                                <div className="min-w-0">
                                  <p className="font-medium truncate">{song.title}</p>
                                  <p className="text-xs text-muted-foreground">Submission #{song.id}</p>
                                </div>
                              </div>
                            </TableCell>
                            <TableCell>
                              <div className="font-medium">{song.artist?.stage_name || "Unknown artist"}</div>
                              <div className="text-xs text-muted-foreground">Artist #{song.artist?.id ?? "N/A"}</div>
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">{song.vote_count.toLocaleString()}</Badge>
                            </TableCell>
                            <TableCell>{formatDuration(song.duration)}</TableCell>
                            <TableCell className="text-muted-foreground">
                              {song.created_at ? new Date(song.created_at).toLocaleString() : "Date unavailable"}
                            </TableCell>
                            <TableCell className="text-right">
                              <div className="flex justify-end gap-2">
                                <Button
                                  size="sm"
                                  variant="outline"
                                  aria-label={`Review ${song.title}`}
                                  onClick={() => {
                                    setSelectedSong(song);
                                    setActionType("approve");
                                  }}
                                >
                                  <Eye className="h-4 w-4" />
                                </Button>
                                <Button
                                  size="sm"
                                  className="bg-green-600 hover:bg-green-700"
                                  aria-label={`Approve ${song.title}`}
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
                                  aria-label={`Reject ${song.title}`}
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
                    </div>
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
                      <CardDescription>
                        Accounts are platform-wide; activity counts reflect {contest?.title || "the active season"}.
                      </CardDescription>
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
                          <SelectItem value="admin">Admins Only</SelectItem>
                          <SelectItem value="active">Active Only</SelectItem>
                        </SelectContent>
                      </Select>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="outline" disabled={isLoadingData}>
                            <Download className="h-4 w-4 mr-2" />
                            Export
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onSelect={() => void exportUsers("pdf")}>Export as PDF</DropdownMenuItem>
                          <DropdownMenuItem onSelect={() => void exportUsers("csv")}>Export as CSV</DropdownMenuItem>
                          <DropdownMenuItem onSelect={() => void exportUsers("xml")}>Export as XML</DropdownMenuItem>
                          <DropdownMenuItem onSelect={() => void exportUsers("excel")}>Export as Excel (.xls)</DropdownMenuItem>
                          <DropdownMenuItem onSelect={() => void exportUsers("jpeg")}>Export as JPEG</DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                  <Table className="min-w-[760px]">
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
                      {isLoadingData ? (
                        <TableRow><TableCell colSpan={6} className="py-10 text-center text-muted-foreground">Loading users...</TableCell></TableRow>
                      ) : filteredUsers.length === 0 ? (
                        <TableRow><TableCell colSpan={6} className="py-10 text-center text-muted-foreground">No matching users found.</TableCell></TableRow>
                      ) : filteredUsers.map((user) => {
                        const role = user.roles.includes("admin") ? "admin" : user.roles.includes("artist") ? "artist" : "user";
                        return (
                        <TableRow key={user.id}>
                          <TableCell>
                            <div className="font-medium">{user.name || user.username}</div>
                            <div className="text-xs text-muted-foreground">{user.email}</div>
                          </TableCell>
                          <TableCell>{getRoleBadge(role)}</TableCell>
                          <TableCell>
                            <div className="flex flex-col items-start gap-1">
                              <Badge className={user.is_active
                                ? "bg-green-500/20 text-green-400 border-green-500/30"
                                : "bg-destructive/20 text-destructive border-destructive/30"}
                              >
                                {user.is_active ? "Account active" : "Account inactive"}
                              </Badge>
                              {getStatusBadge(user.status)}
                            </div>
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {role === "artist"
                              ? `${user.songs_count} songs • ${user.votes_received} votes`
                              : `${user.votes_cast} votes cast`
                            }
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {user.created_at ? new Date(user.created_at).toLocaleDateString() : "—"}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-2">
                              <Button
                                size="sm"
                                variant="outline"
                                aria-label={`View ${user.name || user.username} profile`}
                                onClick={() => setSelectedUser(user)}
                              >
                                <Eye className="h-4 w-4" />
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                aria-label={`Manage ${user.name || user.username} settings`}
                                title="Account settings"
                                disabled
                              >
                                <Settings className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                  </div>
                </CardContent>
              </Card>

              <Card className="glass border-border/50 mt-6">
                <CardHeader>
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <CardTitle>Payment Management</CardTitle>
                      <CardDescription>Review payment records and update their status.</CardDescription>
                    </div>
                    <Select value={paymentFilter} onValueChange={setPaymentFilter}>
                      <SelectTrigger className="w-48">
                        <Filter className="mr-2 h-4 w-4" />
                        <SelectValue placeholder="Filter payments" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Payments</SelectItem>
                        <SelectItem value="pending">Pending Payments</SelectItem>
                        <SelectItem value="successful">Successful Payments</SelectItem>
                        <SelectItem value="reversed">Reversed Payments</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <Table className="min-w-[760px]">
                      <TableHeader>
                        <TableRow>
                          <TableHead>Payment</TableHead>
                          <TableHead>User</TableHead>
                          <TableHead>Season</TableHead>
                          <TableHead>Amount</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Created</TableHead>
                          <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {isLoadingData ? (
                          <TableRow><TableCell colSpan={7} className="py-10 text-center text-muted-foreground">Loading payments...</TableCell></TableRow>
                        ) : filteredPayments.length === 0 ? (
                          <TableRow><TableCell colSpan={7} className="py-10 text-center text-muted-foreground">No matching payments found.</TableCell></TableRow>
                        ) : filteredPayments.map((payment) => (
                          <TableRow key={payment.id}>
                            <TableCell>
                              <div className="font-medium">#{payment.id}</div>
                              <div className="text-xs text-muted-foreground">{payment.tx_ref}</div>
                            </TableCell>
                            <TableCell>
                              <div className="font-medium">{payment.user?.name || payment.user?.username || "Unknown user"}</div>
                              <div className="text-xs text-muted-foreground">{payment.user?.email || "—"}</div>
                            </TableCell>
                            <TableCell>{payment.contest_title || "—"}</TableCell>
                            <TableCell>{formatNaira(payment.amount)}</TableCell>
                            <TableCell>
                              <Badge variant={payment.status === "successful" ? "default" : payment.status === "reversed" ? "destructive" : "secondary"}>
                                {payment.status}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-muted-foreground">
                              {payment.created_at ? new Date(payment.created_at).toLocaleDateString() : "—"}
                            </TableCell>
                            <TableCell className="text-right">
                              <div className="flex justify-end gap-2">
                                <Button
                                  size="sm"
                                  variant="outline"
                                  aria-label={`Edit payment ${payment.id}`}
                                  title="View/edit payment"
                                  onClick={() => {
                                    setSelectedPayment(payment);
                                    setPaymentStatus(
                                      payment.status === "successful" || payment.status === "reversed"
                                        ? payment.status
                                        : "pending",
                                    );
                                  }}
                                >
                                  <Eye className="h-4 w-4" />
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  aria-label={`Manage payment ${payment.id} settings`}
                                  title="Payment settings"
                                  disabled
                                >
                                  <Settings className="h-4 w-4" />
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Analytics Tab */}
            <TabsContent value="analytics">
              <div className="grid md:grid-cols-2 gap-6">
                <Card className="glass border-border/50">
                  <CardHeader>
                    <CardTitle>Voting Trends · {analytics?.contest_title || "No active season"}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {isLoadingData ? (
                      <p className="py-8 text-center text-sm text-muted-foreground" role="status">Loading voting trends...</p>
                    ) : analytics?.daily_votes.length ? (
                      <div className="space-y-3">
                        {analytics.daily_votes.map((day) => (
                          <div key={day.date} className="flex items-center gap-3">
                            <span className="text-sm text-muted-foreground w-16">{day.label}</span>
                            <div className="flex-1 h-6 bg-secondary/50 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-gradient-primary rounded-full transition-all"
                                style={{ width: `${(day.votes / maximumDailyVotes) * 100}%` }}
                              />
                            </div>
                            <span className="text-sm font-medium w-12 text-right">{day.votes.toLocaleString()}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="py-8 text-center text-sm text-muted-foreground">No vote activity recorded yet.</p>
                    )}
                  </CardContent>
                </Card>

                <Card className="glass border-border/50">
                  <CardHeader>
                    <CardTitle>Registrations · {analytics?.contest_title || "No active season"}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {isLoadingData ? (
                      <p className="py-8 text-center text-sm text-muted-foreground" role="status">Loading registrations...</p>
                    ) : analytics ? (
                      <>
                        <div className="grid grid-cols-2 gap-4">
                          <div className="p-4 rounded-lg bg-secondary/50">
                            <p className="text-sm text-muted-foreground">New Artists · 7 days</p>
                            <div className="flex items-end gap-2 mt-2">
                              <span className="text-3xl font-bold text-accent">
                                {analytics.registration_trend.artists_this_week.toLocaleString()}
                              </span>
                              <span className={`text-sm mb-1 ${percentageChange(analytics.registration_trend.artists_this_week, analytics.registration_trend.artists_last_week).startsWith("-") ? "text-red-400" : "text-green-400"}`}>
                                {percentageChange(analytics.registration_trend.artists_this_week, analytics.registration_trend.artists_last_week)}
                              </span>
                            </div>
                            <p className="text-xs text-muted-foreground mt-1">vs previous 7 days</p>
                          </div>
                          <div className="p-4 rounded-lg bg-secondary/50">
                            <p className="text-sm text-muted-foreground">New platform accounts · 7 days</p>
                            <div className="flex items-end gap-2 mt-2">
                              <span className="text-3xl font-bold text-primary">
                                {analytics.registration_trend.users_this_week.toLocaleString()}
                              </span>
                              <span className={`text-sm mb-1 ${percentageChange(analytics.registration_trend.users_this_week, analytics.registration_trend.users_last_week).startsWith("-") ? "text-red-400" : "text-green-400"}`}>
                                {percentageChange(analytics.registration_trend.users_this_week, analytics.registration_trend.users_last_week)}
                              </span>
                            </div>
                            <p className="text-xs text-muted-foreground mt-1">vs previous 7 days</p>
                          </div>
                        </div>
                        <div className="mt-6 p-4 rounded-lg bg-primary/10 border border-primary/30">
                          <h4 className="font-medium mb-2">
                            Revenue {analytics.contest_title ? `· ${analytics.contest_title}` : "· All time"}
                          </h4>
                          <p className="text-2xl font-bold text-primary">{formatNaira(analytics.contest_revenue)}</p>
                          <p className="text-sm text-muted-foreground">Verified successful payments</p>
                        </div>
                      </>
                    ) : (
                      <p className="py-8 text-center text-sm text-muted-foreground">Analytics are not available.</p>
                    )}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </motion.div>
      </main>

      <Dialog
        open={isEditingSeasonDates || isCreatingNewSeason}
        onOpenChange={(open) => {
          if (!open) {
            setIsEditingSeasonDates(false);
            setIsCreatingNewSeason(false);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {isCreatingNewSeason ? "Create New Season" : `Edit ${contest?.title || "season"} dates`}
            </DialogTitle>
            <DialogDescription>
              Set the season start, submission close, and voting end in chronological order.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={isCreatingNewSeason ? saveNewSeason : saveSeasonDates} className="space-y-4">
            <label className="block space-y-2 text-sm">
              <span>Season starts</span>
              <Input
                type="datetime-local"
                value={seasonDateForm.start_date}
                onChange={(event) => setSeasonDateForm((form) => ({ ...form, start_date: event.target.value }))}
                required
              />
            </label>
            <label className="block space-y-2 text-sm">
              <span>Submission closes</span>
              <Input
                type="datetime-local"
                value={seasonDateForm.submission_end_date}
                onChange={(event) => setSeasonDateForm((form) => ({ ...form, submission_end_date: event.target.value }))}
                required
              />
            </label>
            <label className="block space-y-2 text-sm">
              <span>Voting ends</span>
              <Input
                type="datetime-local"
                value={seasonDateForm.voting_end_date}
                onChange={(event) => setSeasonDateForm((form) => ({ ...form, voting_end_date: event.target.value }))}
                required
              />
            </label>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setIsEditingSeasonDates(false);
                  setIsCreatingNewSeason(false);
                }}
                disabled={isSavingSeasonDates}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSavingSeasonDates}>
                {isSavingSeasonDates && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {isSavingSeasonDates ? "Saving..." : isCreatingNewSeason ? "Create season" : "Save dates"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={!!selectedUser} onOpenChange={(open) => !open && setSelectedUser(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{selectedUser?.name || selectedUser?.username} profile</DialogTitle>
            <DialogDescription>Account details and administrator controls.</DialogDescription>
          </DialogHeader>
          {selectedUser && (
            <div className="space-y-4">
              <div className="rounded-lg border border-border/60 bg-secondary/30 p-4">
                <dl className="grid gap-3 text-sm sm:grid-cols-2">
                  <div><dt className="text-muted-foreground">Username</dt><dd className="font-medium">@{selectedUser.username}</dd></div>
                  <div><dt className="text-muted-foreground">Email</dt><dd className="font-medium break-all">{selectedUser.email}</dd></div>
                  <div><dt className="text-muted-foreground">Role</dt><dd>{selectedUser.roles.join(", ") || "user"}</dd></div>
                  <div><dt className="text-muted-foreground">Joined</dt><dd>{selectedUser.created_at ? new Date(selectedUser.created_at).toLocaleString() : "—"}</dd></div>
                  <div><dt className="text-muted-foreground">Account status</dt><dd>{selectedUser.is_active ? "Active" : "Deactivated"}</dd></div>
                </dl>
              </div>
              {selectedUser.artist_profile && (
                <div className="rounded-lg border border-border/60 p-4">
                  <h3 className="mb-2 font-semibold">Artist profile</h3>
                  <p className="text-sm"><span className="text-muted-foreground">Stage name:</span> {selectedUser.artist_profile.stage_name}</p>
                  {selectedUser.artist_profile.genre && (
                    <p className="text-sm"><span className="text-muted-foreground">Genre:</span> {selectedUser.artist_profile.genre}</p>
                  )}
                  {selectedUser.artist_profile.bio && (
                    <p className="mt-2 text-sm text-muted-foreground">{selectedUser.artist_profile.bio}</p>
                  )}
                  <p className="mt-2 text-sm">
                    Payment: {selectedUser.artist_profile.is_paid ? "Paid" : "Not paid"}
                    {selectedUser.artist_profile.is_verified ? " · Verified" : ""}
                  </p>
                </div>
              )}
              <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                <span>{selectedUser.songs_count} songs</span>
                <span>{selectedUser.votes_received} votes received</span>
                <span>{selectedUser.votes_cast} votes cast</span>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedUser(null)}>Close</Button>
            {selectedUser && (
              <Button
                variant={selectedUser.is_active ? "destructive" : "default"}
                onClick={() => void handleUserStatusChange(selectedUser)}
                disabled={
                  isUpdatingUserStatus ||
                  (selectedUser.is_active && String(selectedUser.id) === user?.id)
                }
              >
                {isUpdatingUserStatus
                  ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  : selectedUser.is_active
                    ? <XCircle className="mr-2 h-4 w-4" />
                    : <CheckCircle2 className="mr-2 h-4 w-4" />}
                {selectedUser.is_active ? "Deactivate account" : "Activate account"}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={!!selectedPayment}
        onOpenChange={(open) => !open && setSelectedPayment(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Payment Status</DialogTitle>
            <DialogDescription>
              Update the recorded status for payment #{selectedPayment?.id}.
            </DialogDescription>
          </DialogHeader>
          {selectedPayment && (
            <div className="space-y-4">
              <div className="rounded-lg border border-border/60 bg-secondary/30 p-4 text-sm">
                <p className="font-medium">{selectedPayment.user?.name || selectedPayment.user?.username || "Unknown user"}</p>
                <p className="text-muted-foreground">{selectedPayment.user?.email || "—"}</p>
                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  <p><span className="text-muted-foreground">Amount:</span> {formatNaira(selectedPayment.amount)}</p>
                  <p><span className="text-muted-foreground">Season:</span> {selectedPayment.contest_title || "—"}</p>
                  <p><span className="text-muted-foreground">Reference:</span> {selectedPayment.tx_ref}</p>
                  <p><span className="text-muted-foreground">Created:</span> {selectedPayment.created_at ? new Date(selectedPayment.created_at).toLocaleString() : "—"}</p>
                </div>
              </div>
              <label className="block space-y-2 text-sm">
                <span>Payment status</span>
                <Select value={paymentStatus} onValueChange={setPaymentStatus}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pending">Pending</SelectItem>
                    <SelectItem value="successful">Successful</SelectItem>
                    <SelectItem value="reversed">Reversed</SelectItem>
                  </SelectContent>
                </Select>
              </label>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedPayment(null)} disabled={isUpdatingPaymentStatus}>
              Cancel
            </Button>
            <Button
              onClick={() => void handlePaymentStatusChange()}
              disabled={!selectedPayment || isUpdatingPaymentStatus || paymentStatus === selectedPayment.status}
            >
              {isUpdatingPaymentStatus && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save status
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Approval/Rejection Dialog */}
      <Dialog open={!!selectedSong && !!actionType} onOpenChange={() => { setSelectedSong(null); setActionType(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {actionType === "approve" ? "Approve Song" : "Reject Song"}
            </DialogTitle>
            <DialogDescription>
              {actionType === "approve"
                ? `Review "${selectedSong?.title}" by ${selectedSong?.artist?.stage_name || "Unknown artist"} before approving.`
                : `Please provide a reason for rejecting "${selectedSong?.title}".`
              }
            </DialogDescription>
          </DialogHeader>

          {selectedSong && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 rounded-lg bg-secondary/40 p-3">
                {getMediaUrl(selectedSong.cover_image || selectedSong.artist?.profile_image) ? (
                  <img
                    src={getMediaUrl(selectedSong.cover_image || selectedSong.artist?.profile_image) || undefined}
                    alt=""
                    className="h-14 w-14 rounded-md object-cover"
                  />
                ) : (
                  <div className="h-14 w-14 rounded-md bg-primary/10 flex items-center justify-center">
                    <Music className="h-6 w-6 text-primary" />
                  </div>
                )}
                <div className="min-w-0">
                  <p className="font-semibold truncate">{selectedSong.title}</p>
                  <p className="text-sm text-muted-foreground">
                    {selectedSong.artist?.stage_name || "Unknown artist"} · {formatDuration(selectedSong.duration)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Submitted {selectedSong.created_at ? new Date(selectedSong.created_at).toLocaleString() : "date unavailable"}
                  </p>
                </div>
              </div>
              <audio
                controls
                preload="none"
                src={getMediaUrl(selectedSong.audio_url) || undefined}
                className="w-full"
              >
                Your browser does not support audio playback.
              </audio>
            </div>
          )}
          
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
              onClick={() => selectedSong && actionType && void handleSongAction(String(selectedSong.id), actionType)}
              disabled={isSongActionLoading || (actionType === "reject" && !rejectionReason.trim())}
            >
              {isSongActionLoading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {isSongActionLoading
                ? "Saving..."
                : actionType === "approve" ? "Approve Song" : "Reject Song"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Admin;
