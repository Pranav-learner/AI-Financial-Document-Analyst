/**
 * TanStack Query hooks for agent/chat interactions.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listThreads,
  getThread,
  getMessages,
  sendMessage,
  createThread,
} from "@/services/agentService";
import type { ChatPayload } from "@/services/agentService";

export function useThreads() {
  return useQuery({
    queryKey: ["threads"],
    queryFn: ({ signal }) => listThreads(100, 0, signal),
    staleTime: 30 * 1000,
  });
}

export function useThread(threadId: string | undefined) {
  return useQuery({
    queryKey: ["thread", threadId],
    queryFn: ({ signal }) => getThread(threadId!, signal),
    enabled: !!threadId,
  });
}

export function useMessages(threadId: string | undefined) {
  return useQuery({
    queryKey: ["messages", threadId],
    queryFn: ({ signal }) => getMessages(threadId!, signal),
    enabled: !!threadId,
    refetchInterval: false,
  });
}

export function useSendMessage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ChatPayload) => sendMessage(payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({
        queryKey: ["messages", variables.thread_id],
      });
    },
  });
}

export function useCreateThread() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (companyId?: string) => createThread(companyId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["threads"] });
    },
  });
}
