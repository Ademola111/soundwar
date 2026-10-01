import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";
import { API_ENDPOINTS, getAuthHeaders } from "@/config/api";
import { useAuth } from "@/contexts/AuthContext";

interface VoteInfo {
  hasVoted: boolean;
  votedSongId: string | null;
  votedAt: string | null;
  contestId: string | null;
}

interface VotingContextType {
  voteInfo: VoteInfo;
  isLoading: boolean;
  castVote: (songId: string) => Promise<{ success: boolean; error?: string }>;
  checkVoteStatus: (showLoading?: boolean) => Promise<void>;
  isVoteDisabled: boolean;
}

const defaultVoteInfo: VoteInfo = {
  hasVoted: false,
  votedSongId: null,
  votedAt: null,
  contestId: null,
};

const VotingContext = createContext<VotingContextType | undefined>(undefined);

export const VotingProvider = ({ children }: { children: ReactNode }) => {
  const { token } = useAuth();
  const [voteInfo, setVoteInfo] = useState<VoteInfo>(defaultVoteInfo);
  const [isLoading, setIsLoading] = useState(true);

  // Check user's vote status on mount
  const checkVoteStatus = useCallback(async (showLoading = true) => {
    if (!token) {
      setVoteInfo(defaultVoteInfo);
      localStorage.removeItem("user_vote");
      setIsLoading(false);
      return;
    }

    if (showLoading) {
      setIsLoading(true);
      setVoteInfo(defaultVoteInfo);
    }
    try {
      const response = await fetch(API_ENDPOINTS.VOTES.MY_VOTE, {
        headers: getAuthHeaders(token),
      });

      if (!response.ok) {
        throw new Error("Could not check your vote status.");
      }

      const data = await response.json() as {
        vote?: { song_id?: number; created_at?: string; contest_id?: number } | null;
      };
      const vote = data.vote;
      setVoteInfo(vote ? {
        hasVoted: true,
        votedSongId: vote.song_id?.toString() || null,
        votedAt: vote.created_at || null,
        contestId: vote.contest_id?.toString() || null,
      } : defaultVoteInfo);
    } catch (error) {
      console.error("Failed to check vote status:", error);
      if (showLoading) setVoteInfo(defaultVoteInfo);
    } finally {
      if (showLoading) setIsLoading(false);
    }
  }, [token]);

  const castVote = async (songId: string): Promise<{ success: boolean; error?: string }> => {
    const token = localStorage.getItem("auth_token");
    
    // Security check: Prevent voting if already voted
    if (voteInfo.hasVoted) {
      return { 
        success: false, 
        error: "You have already voted in this contest. Each user can only vote once." 
      };
    }

    if (!token) {
      return { success: false, error: "Please login to vote" };
    }

    setIsLoading(true);
    try {
      const response = await fetch(API_ENDPOINTS.VOTES.CAST, {
        method: "POST",
        headers: getAuthHeaders(token),
        body: JSON.stringify({ song_id: songId }),
      });

      const data = await response.json();

      if (response.ok) {
        const newVoteInfo = {
          hasVoted: true,
          votedSongId: songId,
          votedAt: data.vote?.created_at || new Date().toISOString(),
          contestId: data.vote?.contest_id?.toString() || null,
        };
        setVoteInfo(newVoteInfo);
        localStorage.removeItem("user_vote");

        return { success: true };
      } else {
        if (response.status === 409) {
          setVoteInfo({
            hasVoted: true,
            votedSongId: data.voted_song_id?.toString() || null,
            votedAt: null,
            contestId: null,
          });
        }
        return { success: false, error: data.error || "Failed to cast vote" };
      }
    } catch {
      return { success: false, error: "Unable to reach the voting service. Please try again." };
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void checkVoteStatus();
    if (!token) return;

    const refreshInterval = window.setInterval(() => {
      void checkVoteStatus(false);
    }, 30_000);

    return () => window.clearInterval(refreshInterval);
  }, [checkVoteStatus, token]);

  return (
    <VotingContext.Provider
      value={{
        voteInfo,
        isLoading,
        castVote,
        checkVoteStatus,
        isVoteDisabled: voteInfo.hasVoted,
      }}
    >
      {children}
    </VotingContext.Provider>
  );
};

export const useVoting = (): VotingContextType => {
  const context = useContext(VotingContext);
  if (context === undefined) {
    throw new Error("useVoting must be used within a VotingProvider");
  }
  return context;
};
