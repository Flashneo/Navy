"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RunDialog } from "@/components/run-dialog";
import { TelegramButton } from "@/components/telegram-button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api, type Run, type ActiveRun } from "@/lib/api";

export default function RunsPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [activeRun, setActiveRun] = useState<ActiveRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [stopping, setStopping] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [runsData, activeData] = await Promise.all([
        api.getRuns(),
        api.getActiveRun(),
      ]);
      setRuns(runsData.runs);
      setActiveRun(activeData);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Poll for active run status + refresh runs table
  useEffect(() => {
    if (!activeRun?.active) return;
    const interval = setInterval(async () => {
      const [activeData, runsData] = await Promise.all([
        api.getActiveRun(),
        api.getRuns(),
      ]);
      setActiveRun(activeData);
      setRuns(runsData.runs);
      if (!activeData.active) {
        clearInterval(interval);
        setStopping(false);
        fetchData();
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [activeRun?.active, fetchData]);

  const handleStopRun = async () => {
    setStopping(true);
    try {
      await api.stopRun();
      setTimeout(fetchData, 2000);
    } catch {}
    setStopping(false);
  };

  const statusBadge = (status: string) => {
    const variant =
      status === "success"
        ? "default"
        : status === "running"
        ? "secondary"
        : status === "failed"
        ? "destructive"
        : "outline";
    return <Badge variant={variant}>{status}</Badge>;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">Loading runs...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Runs</h2>
          <p className="text-muted-foreground">Pipeline execution history</p>
        </div>
        <div className="flex gap-2">
          <TelegramButton />
          <RunDialog />
        </div>
      </div>

      {/* Active Run Banner */}
      {activeRun?.active && (activeRun?.status === "running" || activeRun?.status === "stopping") && (
        <Card className="border-primary/30 bg-primary/5">
          <CardContent className="pt-4 pb-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-3 w-3 rounded-full bg-primary animate-pulse" />
                <span className="font-medium">
                  {activeRun.status === "stopping" ? "Stopping..." : "Pipeline is running..."}
                </span>
                {activeRun.progress?.step && (
                  <Badge variant="outline" className="font-normal">
                    {activeRun.progress.step}
                  </Badge>
                )}
                <span className="text-sm text-muted-foreground">
                  {activeRun.dry_run ? "(Dry Run)" : ""}
                  {activeRun.skip_enrichment ? "(No Enrichment)" : ""}
                </span>
              </div>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleStopRun}
                disabled={stopping || activeRun.status === "stopping"}
              >
                {stopping || activeRun.status === "stopping" ? "Stopping..." : "Stop Run"}
              </Button>
            </div>
            {activeRun.progress && (
              <div className="flex gap-8 text-sm">
                <div>
                  <span className="text-muted-foreground">Found: </span>
                  <span className="font-bold text-lg">{activeRun.progress.jobs_found}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">New: </span>
                  <span className="font-bold text-lg text-emerald-600">{activeRun.progress.jobs_new}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Passed: </span>
                  <span className="font-bold text-lg">{activeRun.progress.jobs_passed}</span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Runs Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[60px]">ID</TableHead>
              <TableHead>Started</TableHead>
              <TableHead>Completed</TableHead>
              <TableHead className="text-right">Found</TableHead>
              <TableHead className="text-right">New</TableHead>
              <TableHead className="text-right">Passed</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {runs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                  No runs yet. Click &quot;New Run&quot; to start.
                </TableCell>
              </TableRow>
            ) : (
              runs.map((run) => (
                <TableRow key={run.id}>
                  <TableCell className="font-mono text-sm">#{run.id}</TableCell>
                  <TableCell className="text-sm">{run.started_at || "—"}</TableCell>
                  <TableCell className="text-sm">{run.completed_at || "—"}</TableCell>
                  <TableCell className="text-right font-medium">{run.jobs_found}</TableCell>
                  <TableCell className="text-right font-medium text-emerald-600">
                    {run.jobs_new}
                  </TableCell>
                  <TableCell className="text-right font-medium">{run.jobs_passed_filter}</TableCell>
                  <TableCell>{statusBadge(run.status)}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
