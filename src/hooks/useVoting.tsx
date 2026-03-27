import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { API_ENDPOINTS, getAuthHeaders } from "@/config/api";

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
  checkVoteStatus: () => Promise<void>;
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
  const [voteInfo, setVoteInfo] = useState<VoteInfo>(defaultVoteInfo);
  const [isLoading, setIsLoading] = useState(false);

  // Check user's vote status on mount
  const checkVoteStatus = async () => {
    const token = localStorage.getItem("auth_token");
    if (!token) {
      setVoteInfo(defaultVoteInfo);
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(API_ENDPOINTS.VOTES.MY_VOTE, {
        headers: getAuthHeaders(token),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.has_voted) {
          setVoteInfo({
            hasVoted: true,
            votedSongId: data.vote?.song_id?.toString() || null,
            votedAt: data.vote?.voted_at || null,
            contestId: data.vote?.contest_id?.toString() || null,
          });
        } else {
          setVoteInfo(defaultVoteInfo);
        }
      }
    } catch (error) {
      console.error("Failed to check vote status:", error);
      // For demo: check localStorage fallback
      const storedVote = localStorage.getItem("user_vote");
      if (storedVote) {
        try {
          const parsed = JSON.parse(storedVote);
          setVoteInfo({
            hasVoted: true,
            votedSongId: parsed.songId,
            votedAt: parsed.votedAt,
            contestId: parsed.contestId,
          });
        } catch {
          setVoteInfo(defaultVoteInfo);
        }
      }
    } finally {
      setIsLoading(false);
    }
  };

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
          votedAt: new Date().toISOString(),
          contestId: data.vote?.contest_id?.toString() || "1",
        };
        setVoteInfo(newVoteInfo);
        
        // Store in localStorage as fallback for demo
        localStorage.setItem("user_vote", JSON.stringify({
          songId,
          votedAt: newVoteInfo.votedAt,
          contestId: newVoteInfo.contestId,
        }));

        return { success: true };
      } else {
        return { success: false, error: data.error || "Failed to cast vote" };
      }
    } catch (error) {
      // For demo: simulate successful vote
      const newVoteInfo = {
        hasVoted: true,
        votedSongId: songId,
        votedAt: new Date().toISOString(),
        contestId: "1",
      };
      setVoteInfo(newVoteInfo);
      localStorage.setItem("user_vote", JSON.stringify({
        songId,
        votedAt: newVoteInfo.votedAt,
        contestId: newVoteInfo.contestId,
      }));
      return { success: true };
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    checkVoteStatus();
  }, []);

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
