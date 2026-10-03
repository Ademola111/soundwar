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

interface CurrentUserResponse {
  user?: {
    artist_profile?: {
      is_paid?: boolean;
      requires_season_payment?: boolean;
    } | null;
  };
}

type ContestSubmissionState =
  | "eligible"
  | "unpaid"
  | "no-contest"
  | "outside-submission"
  | "already-submitted";

const getContestSubmissionState = async (token: string): Promise<ContestSubmissionState> => {
  const [contestResponse, submissionsResponse, userResponse] = await Promise.all([
    fetch(API_ENDPOINTS.LEADERBOARD.BASE),
    fetch(API_ENDPOINTS.SONGS.MY_SUBMISSIONS, { headers: getAuthHeaders(token) }),
    fetch(API_ENDPOINTS.AUTH.ME, { headers: getAuthHeaders(token) }),
  ]);

  if (!contestResponse.ok || !submissionsResponse.ok || !userResponse.ok) {
    throw new Error("Could not check song submission eligibility.");
  }

  const [contestData, submissionsData, userData] = await Promise.all([
    contestResponse.json() as Promise<ActiveContestResponse>,
    submissionsResponse.json() as Promise<MySubmissionsResponse>,
    userResponse.json() as Promise<CurrentUserResponse>,
  ]);

  const artist = userData.user?.artist_profile;
  if (!artist?.is_paid || artist.requires_season_payment) return "unpaid";
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
    !isAuthLoading &&
      isAuthenticated &&
      token &&
      artist &&
      artist?.is_paid &&
      !artist.requires_season_payment &&
      artist.can_participate !== false,
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
  } else if (!artist.is_paid || artist.requires_season_payment) {
    reason = "unpaid";
  } else if (artist.can_participate === false) {
    reason = "ineligible";
  } else if (query.data === "unpaid") {
    reason = "unpaid";
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
