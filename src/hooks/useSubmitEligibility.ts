import { useQuery } from "@tanstack/react-query";
import { API_ENDPOINTS, getAuthHeaders } from "@/config/api";
import { useAuth } from "@/contexts/AuthContext";

interface ActiveContestResponse {
  contest: {
    id: number;
    phase: string;
  } | null;
}

interface MySubmissionsResponse {
  songs: Array<{ contest_id: number }>;
}

type ContestSubmissionState = "eligible" | "no-contest" | "outside-submission" | "already-submitted";

const getContestSubmissionState = async (token: string): Promise<ContestSubmissionState> => {
  const [contestResponse, submissionsResponse] = await Promise.all([
    fetch(API_ENDPOINTS.LEADERBOARD.BASE),
    fetch(API_ENDPOINTS.SONGS.MY_SUBMISSIONS, { headers: getAuthHeaders(token) }),
  ]);

  if (!contestResponse.ok || !submissionsResponse.ok) {
    throw new Error("Could not check song submission eligibility.");
  }

  const [contestData, submissionsData] = await Promise.all([
    contestResponse.json() as Promise<ActiveContestResponse>,
    submissionsResponse.json() as Promise<MySubmissionsResponse>,
  ]);

  if (!contestData.contest) return "no-contest";
  if (contestData.contest.phase !== "submission") return "outside-submission";
  if (submissionsData.songs.some((song) => song.contest_id === contestData.contest?.id)) {
    return "already-submitted";
  }

  return "eligible";
};

export const useSubmitEligibility = () => {
  const { user, token, isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const artist = user?.artist_profile;
  const canCheckServerEligibility = Boolean(
    !isAuthLoading && isAuthenticated && token && artist?.is_paid && artist.can_participate !== false,
  );
  const query = useQuery({
    queryKey: ["song-submission-eligibility", user?.id],
    queryFn: () => getContestSubmissionState(token!),
    enabled: canCheckServerEligibility,
    refetchInterval: 30_000,
  });

  let reason: string;
  if (isAuthLoading || (canCheckServerEligibility && query.isLoading)) {
    reason = "checking";
  } else if (!isAuthenticated) {
    reason = "unauthenticated";
  } else if (!artist) {
    reason = "not-artist";
  } else if (!artist.is_paid) {
    reason = "unpaid";
  } else if (artist.can_participate === false) {
    reason = "ineligible";
  } else if (query.isError) {
    reason = "unavailable";
  } else {
    reason = query.data || "checking";
  }

  return {
    canSubmitSong: reason === "eligible",
    isChecking: reason === "checking",
    reason,
  };
};
