import { useState, useEffect, useCallback } from "react";
import { query, mutate, healthCheck } from "../lib/insforge";

/**
 * Hook para consultas SELECT a Insforge con estado de carga y error.
 */
export function useInsforgeQuery(sql, params = [], deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await query(sql, params);
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [sql, ...params, ...deps]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, loading, error, refetch };
}

/**
 * Hook para mutaciones (INSERT/UPDATE/DELETE) con feedback.
 */
export function useInsforgeMutate() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const run = useCallback(async (sql, params = []) => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await mutate(sql, params);
      setSuccess(true);
      return result;
    } catch (err) {
      setError(err.message);
      setSuccess(false);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setError(null);
    setSuccess(null);
  }, []);

  return { run, loading, error, success, reset };
}

/**
 * Hook para el estado de conexión con Insforge.
 */
export function useInsforgeHealth() {
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    healthCheck().then((result) => {
      setStatus(result.ok ? "connected" : "error");
    });
  }, []);

  return status;
}
