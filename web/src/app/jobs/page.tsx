"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ScoreBadge } from "@/components/score-badge";
import { RunDialog } from "@/components/run-dialog";
import { TelegramButton } from "@/components/telegram-button";
import { api, type Job, type JobsResponse } from "@/lib/api";

export default function JobsPage() {
  const [data, setData] = useState<JobsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [minScore, setMinScore] = useState("0");
  const [page, setPage] = useState(1);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState("relevance_score");
  const [sortOrder, setSortOrder] = useState("desc");

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    try {
      const result = await api.getJobs({
        q: search || undefined,
        min_score: parseFloat(minScore) || undefined,
        page,
        per_page: 20,
        sort_by: sortBy,
        sort_order: sortOrder,
      });
      setData(result);
    } catch {
      // handle error
    }
    setLoading(false);
  }, [search, minScore, page, sortBy, sortOrder]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const handleSearch = () => {
    setPage(1);
    fetchJobs();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Jobs</h2>
          <p className="text-muted-foreground">
            {data ? `${data.total} jobs found` : "Loading..."}
          </p>
        </div>
        <div className="flex gap-2">
          <TelegramButton />
          <RunDialog />
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-4 pb-4">
          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="text-xs font-medium text-muted-foreground mb-1 block">
                Search
              </label>
              <Input
                placeholder="Search title, company, description..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              />
            </div>
            <div className="w-[140px]">
              <label className="text-xs font-medium text-muted-foreground mb-1 block">
                Min Score
              </label>
              <Select value={minScore} onValueChange={(v) => { setMinScore(v ?? "0"); setPage(1); }}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="0">All</SelectItem>
                  <SelectItem value="0.8">80%+</SelectItem>
                  <SelectItem value="0.6">60%+</SelectItem>
                  <SelectItem value="0.4">40%+</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="w-[160px]">
              <label className="text-xs font-medium text-muted-foreground mb-1 block">
                Sort By
              </label>
              <Select value={sortBy} onValueChange={(v) => { setSortBy(v ?? "relevance_score"); setPage(1); }}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="relevance_score">Score</SelectItem>
                  <SelectItem value="posted_date">Date Posted</SelectItem>
                  <SelectItem value="first_seen_at">Date Found</SelectItem>
                  <SelectItem value="company_name">Company</SelectItem>
                  <SelectItem value="title">Title</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button onClick={handleSearch}>Search</Button>
            <div className="flex gap-2">
              <a href={api.getExportUrl("csv")} target="_blank" rel="noopener noreferrer">
                <Button variant="outline" size="sm">Export CSV</Button>
              </a>
              <a href={api.getExportUrl("json")} target="_blank" rel="noopener noreferrer">
                <Button variant="outline" size="sm">Export JSON</Button>
              </a>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Jobs Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[70px]">Score</TableHead>
              <TableHead>Title</TableHead>
              <TableHead>Company</TableHead>
              <TableHead>Location</TableHead>
              <TableHead className="w-[100px]">Seniority</TableHead>
              <TableHead className="w-[90px]">Posted</TableHead>
              <TableHead className="w-[70px]">Link</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data?.jobs.map((job) => (
              <React.Fragment key={job.linkedin_id}>
                <TableRow
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() =>
                    setExpandedId(expandedId === job.linkedin_id ? null : job.linkedin_id)
                  }
                >
                  <TableCell>
                    <ScoreBadge score={job.relevance_score} />
                  </TableCell>
                  <TableCell className="font-medium max-w-[250px] truncate">
                    {job.title}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{job.company_name}</TableCell>
                  <TableCell className="text-muted-foreground text-sm max-w-[150px] truncate">
                    {job.location}
                  </TableCell>
                  <TableCell>
                    {job.seniority_level && (
                      <Badge variant="outline" className="text-[10px]">
                        {job.seniority_level}
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {job.posted_date || "—"}
                  </TableCell>
                  <TableCell>
                    <a
                      href={job.job_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Button variant="ghost" size="sm">Open</Button>
                    </a>
                  </TableCell>
                </TableRow>
                {expandedId === job.linkedin_id && (
                  <TableRow>
                    <TableCell colSpan={7} className="bg-muted/30">
                      <div className="p-4 space-y-3">
                        {job.score_reasoning && (
                          <div>
                            <span className="text-xs font-medium text-muted-foreground">
                              Score Reasoning:
                            </span>
                            <p className="text-sm">{job.score_reasoning}</p>
                          </div>
                        )}
                        {job.matched_keywords.length > 0 && (
                          <div>
                            <span className="text-xs font-medium text-muted-foreground">
                              Matched Keywords:
                            </span>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {job.matched_keywords.map((kw) => (
                                <Badge key={kw} variant="secondary" className="text-xs">
                                  {kw}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}
                        <div className="flex gap-4 text-xs text-muted-foreground">
                          <span>Type: {job.employment_type || "N/A"}</span>
                          <span>Found: {job.first_seen_at}</span>
                        </div>
                      </div>
                    </TableCell>
                  </TableRow>
                )}
              </React.Fragment>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* Pagination */}
      {data && data.pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {data.page} of {data.pages} ({data.total} total)
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= data.pages}
              onClick={() => setPage(page + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
