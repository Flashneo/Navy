"use client";

import { useState } from "react";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

export function RunDialog() {
  const [open, setOpen] = useState(false);
  const [dryRun, setDryRun] = useState(false);
  const [skipEnrichment, setSkipEnrichment] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [started, setStarted] = useState(false);

  const handleRun = async () => {
    setTriggering(true);
    try {
      const res = await api.triggerRun({ dry_run: dryRun, skip_enrichment: skipEnrichment });
      if (!("error" in res)) {
        setStarted(true);
        setTimeout(() => {
          setOpen(false);
          setStarted(false);
        }, 1500);
      }
    } catch {}
    setTriggering(false);
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); setStarted(false); }}>
      <DialogTrigger className={cn(buttonVariants({ variant: "default", size: "default" }))}>
        New Run
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Start New Pipeline Run</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 pt-4">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
              className="rounded border-gray-300"
            />
            <div>
              <p className="text-sm font-medium">Dry Run</p>
              <p className="text-xs text-muted-foreground">
                Use keyword scoring instead of AI (no API key needed)
              </p>
            </div>
          </label>
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={skipEnrichment}
              onChange={(e) => setSkipEnrichment(e.target.checked)}
              className="rounded border-gray-300"
            />
            <div>
              <p className="text-sm font-medium">Skip Enrichment</p>
              <p className="text-xs text-muted-foreground">
                Skip company size data fetching (faster)
              </p>
            </div>
          </label>
          {started ? (
            <div className="text-center text-sm text-emerald-600 font-medium py-2">
              Pipeline started! Check the Runs page for progress.
            </div>
          ) : (
            <Button onClick={handleRun} disabled={triggering} className="w-full">
              {triggering ? "Starting..." : "Start Run"}
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
