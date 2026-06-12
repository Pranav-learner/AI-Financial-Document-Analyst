/**
 * Agent service — threads, messages, chat.
 */

import { get, post } from "./api";
import type { Thread, Message, ChatResponse } from "@/types/api";

export interface ChatPayload {
  query: string;
  thread_id: string;
  company_id?: string;
}

export function createThread(
  companyId?: string,
  signal?: AbortSignal,
): Promise<Thread> {
  return post<Thread>(
    "/agent/threads",
    companyId ? { company_id: companyId } : {},
    signal,
  );
}

export function listThreads(
  limit = 100,
  offset = 0,
  signal?: AbortSignal,
): Promise<Thread[]> {
  return get<Thread[]>(
    `/agent/threads?limit=${limit}&offset=${offset}`,
    signal,
  );
}

export function getThread(
  threadId: string,
  signal?: AbortSignal,
): Promise<Thread> {
  return get<Thread>(`/agent/threads/${threadId}`, signal);
}

export function getMessages(
  threadId: string,
  signal?: AbortSignal,
): Promise<Message[]> {
  return get<Message[]>(`/agent/threads/${threadId}/messages`, signal);
}

export function sendMessage(
  payload: ChatPayload,
  signal?: AbortSignal,
): Promise<ChatResponse> {
  return post<ChatResponse>("/agent/chat", payload, signal);
}
