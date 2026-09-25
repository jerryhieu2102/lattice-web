"use client";
import { useState } from "react";
import { ZodError } from "zod";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import type { Notify } from "./types";
export function useData<T>(key: string, path: string, enabled = true) {
  return useQuery({
    queryKey: [key, path],
    queryFn: () => api<T>(path),
    enabled,
  });
}
export function useTask(notify: Notify) {
  const client = useQueryClient();
  const [busy, setBusy] = useState(false);
  async function run<T>(work: () => Promise<T>, message: string) {
    setBusy(true);
    try {
      const result = await work();
      await client.invalidateQueries();
      notify(message);
      return result;
    } catch (e) {
      notify(
        e instanceof ZodError
          ? "Invalid input. Check all required fields, amounts, dates, and currency precision."
          : (e as Error).message,
        true,
      );
    } finally {
      setBusy(false);
    }
  }
  return { busy, run };
}
