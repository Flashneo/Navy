"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScoreBadge } from "@/components/score-badge";
import { api, type Stats, type Job } from "@/lib/api";
import { RunDialog } from "@/components/run-dialog";
import { TelegramButton } from "@/components/telegram-button";
import Link from "next/link";

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [topJobs, setTopJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      api.getStats(),
      api.getJobs({ per_page: 10, sort_by: "relevance_score", sort_order: "desc" }),
    ]).then(([statsData, jobsData]) => {
      setStats(statsData);
      setTopJobs(jobsData.jobs);
      setLoading(false);
    }).catch((e) => {
      setError(e?.message || "Failed to connect to API");
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">Loading dashboard...</div>
      </div>
    );
  }

  if (error || !stats) return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
          <p className="text-muted-foreground">Overview of your job search agent</p>
        </div>
      </div>
      <Card>
        <CardContent className="pt-6">
          <div className="text-center space-y-2">
            <p className="text-lg font-medium">Cannot connect to API server</p>
            <p className="text-sm text-muted-foreground">{error}</p>
            <Button onClick={() => window.location.reload()} variant="outline" className="mt-4">
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
          <p className="text-muted-foreground">Overview of your job search agent</p>
        </div>
        <div className="flex gap-2">
          <TelegramButton />
          <RunDialog />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.total_jobs}</div>
            <p className="text-xs text-muted-foreground">in database</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">New This Week</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-emerald-600">{stats.new_this_week}</div>
            <p className="text-xs text-muted-foreground">last 7 days</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Relevance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{(stats.avg_score * 100).toFixed(0)}%</div>
            <p className="text-xs text-muted-foreground">average score</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Runs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.total_runs}</div>
            <p className="text-xs text-muted-foreground">
              {stats.last_run ? `Last: ${stats.last_run.status}` : "No runs yet"}
            </p>
          </CardContent>
        </Card>
      </div>

      {stats.last_run && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Last Run Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-6 text-sm">
              <div>
                <span className="text-muted-foreground">Status: </span>
                <Badge variant={stats.last_run.status === "success" ? "default" : "destructive"}>
                  {stats.last_run.status}
                </Badge>
              </div>
              <div>
                <span className="text-muted-foreground">Found: </span>
                <span className="font-medium">{stats.last_run.jobs_found}</span>
              </div>
              <div>
                <span className="text-muted-foreground">New: </span>
                <span className="font-medium">{stats.last_run.jobs_new}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Passed: </span>
                <span className="font-medium">{stats.last_run.jobs_passed_filter}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {stats.top_companies.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Top Companies</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {stats.top_companies.map((c) => (
                <Badge key={c.name} variant="secondary" className="text-sm">
                  {c.name} ({c.count})
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Top Scored Jobs</h3>
          <Link href="/jobs">
            <Button variant="outline" size="sm">View All Jobs</Button>
          </Link>
        </div>
        <div className="grid gap-3">
          {topJobs.map((job) => (
            <Card key={job.linkedin_id} className="hover:border-primary/30 transition-colors">
              <CardContent className="pt-4 pb-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <ScoreBadge score={job.relevance_score} />
                      <h4 className="font-semibold truncate">{job.title}</h4>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {job.company_name} — {job.location}
                    </p>
                    {job.matched_keywords.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {job.matched_keywords.slice(0, 5).map((kw) => (
                          <Badge key={kw} variant="outline" className="text-[10px] px-1.5 py-0">
                            {kw}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                  <a
                    href={job.job_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="shrink-0"
                  >
                    <Button variant="outline" size="sm">Open</Button>
                  </a>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
