"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { TelegramButton } from "@/components/telegram-button";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [newKeyword, setNewKeyword] = useState("");
  const [newLocation, setNewLocation] = useState("");

  useEffect(() => {
    api.getConfig().then((data) => {
      setConfig(data);
      setLoading(false);
    });
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.updateConfig(config);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {}
    setSaving(false);
  };

  const addKeyword = () => {
    if (newKeyword.trim() && !config.search.keywords.includes(newKeyword.trim())) {
      setConfig({
        ...config,
        search: {
          ...config.search,
          keywords: [...config.search.keywords, newKeyword.trim()],
        },
      });
      setNewKeyword("");
    }
  };

  const removeKeyword = (kw: string) => {
    setConfig({
      ...config,
      search: {
        ...config.search,
        keywords: config.search.keywords.filter((k: string) => k !== kw),
      },
    });
  };

  const addLocation = () => {
    if (newLocation.trim() && !config.search.locations.includes(newLocation.trim())) {
      setConfig({
        ...config,
        search: {
          ...config.search,
          locations: [...config.search.locations, newLocation.trim()],
        },
      });
      setNewLocation("");
    }
  };

  const removeLocation = (loc: string) => {
    setConfig({
      ...config,
      search: {
        ...config.search,
        locations: config.search.locations.filter((l: string) => l !== loc),
      },
    });
  };

  const toggleTimeFilter = (tf: string) => {
    const current = config.search.time_filters;
    const updated = current.includes(tf)
      ? current.filter((t: string) => t !== tf)
      : [...current, tf];
    setConfig({
      ...config,
      search: { ...config.search, time_filters: updated },
    });
  };

  const toggleRemoteFilter = (rf: string) => {
    const current = config.search.remote_filters;
    const updated = current.includes(rf)
      ? current.filter((r: string) => r !== rf)
      : [...current, rf];
    setConfig({
      ...config,
      search: { ...config.search, remote_filters: updated },
    });
  };

  if (loading || !config) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">Loading settings...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Settings</h2>
          <p className="text-muted-foreground">Configure your job search agent</p>
        </div>
        <div className="flex items-center gap-3">
          {saved && (
            <span className="text-sm text-emerald-600 font-medium">Saved!</span>
          )}
          <TelegramButton />
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : "Save Changes"}
          </Button>
        </div>
      </div>

      <Tabs defaultValue="search" className="space-y-4">
        <TabsList>
          <TabsTrigger value="search">Search</TabsTrigger>
          <TabsTrigger value="filtering">Filtering</TabsTrigger>
          <TabsTrigger value="scoring">Scoring</TabsTrigger>
          <TabsTrigger value="rate">Rate Limiting</TabsTrigger>
        </TabsList>

        {/* Search Tab */}
        <TabsContent value="search" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Keywords</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap gap-2">
                {config.search.keywords.map((kw: string) => (
                  <Badge
                    key={kw}
                    variant="secondary"
                    className="text-sm cursor-pointer hover:bg-destructive/20"
                    onClick={() => removeKeyword(kw)}
                  >
                    {kw} ×
                  </Badge>
                ))}
              </div>
              <div className="flex gap-2">
                <Input
                  placeholder="Add keyword..."
                  value={newKeyword}
                  onChange={(e) => setNewKeyword(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addKeyword()}
                />
                <Button variant="outline" onClick={addKeyword}>Add</Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Locations</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap gap-2">
                {config.search.locations.map((loc: string) => (
                  <Badge
                    key={loc}
                    variant="secondary"
                    className="text-sm cursor-pointer hover:bg-destructive/20"
                    onClick={() => removeLocation(loc)}
                  >
                    {loc} ×
                  </Badge>
                ))}
              </div>
              <div className="flex gap-2">
                <Input
                  placeholder="Add location..."
                  value={newLocation}
                  onChange={(e) => setNewLocation(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addLocation()}
                />
                <Button variant="outline" onClick={addLocation}>Add</Button>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Time Filter</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {[
                  { value: "r86400", label: "Last 24 hours" },
                  { value: "r604800", label: "Last week" },
                  { value: "r2592000", label: "Last month" },
                ].map((tf) => (
                  <label key={tf.value} className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.search.time_filters.includes(tf.value)}
                      onChange={() => toggleTimeFilter(tf.value)}
                      className="rounded"
                    />
                    <span className="text-sm">{tf.label}</span>
                  </label>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Remote / On-site</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {[
                  { value: "1", label: "On-site" },
                  { value: "2", label: "Remote" },
                  { value: "3", label: "Hybrid" },
                ].map((rf) => (
                  <label key={rf.value} className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.search.remote_filters.includes(rf.value)}
                      onChange={() => toggleRemoteFilter(rf.value)}
                      className="rounded"
                    />
                    <span className="text-sm">{rf.label}</span>
                  </label>
                ))}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Experience Level</CardTitle>
            </CardHeader>
            <CardContent>
              <Select
                value={config.search.experience_level}
                onValueChange={(v) =>
                  setConfig({
                    ...config,
                    search: { ...config.search, experience_level: v },
                  })
                }
              >
                <SelectTrigger className="w-[250px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">Internship</SelectItem>
                  <SelectItem value="2">Entry level</SelectItem>
                  <SelectItem value="3">Associate</SelectItem>
                  <SelectItem value="4">Mid-Senior level</SelectItem>
                  <SelectItem value="5">Director</SelectItem>
                  <SelectItem value="6">Executive</SelectItem>
                </SelectContent>
              </Select>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Filtering Tab */}
        <TabsContent value="filtering" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Company Size Ranges</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {Object.entries(config.filtering.company_size).map(
                ([category, range]: [string, any]) => (
                  <div key={category} className="flex items-center gap-4">
                    <span className="text-sm font-medium w-20 capitalize">{category}:</span>
                    <Input
                      type="number"
                      className="w-24"
                      value={range.min}
                      onChange={(e) =>
                        setConfig({
                          ...config,
                          filtering: {
                            ...config.filtering,
                            company_size: {
                              ...config.filtering.company_size,
                              [category]: { ...range, min: parseInt(e.target.value) || 0 },
                            },
                          },
                        })
                      }
                    />
                    <span className="text-muted-foreground">to</span>
                    <Input
                      type="number"
                      className="w-24"
                      value={range.max}
                      onChange={(e) =>
                        setConfig({
                          ...config,
                          filtering: {
                            ...config.filtering,
                            company_size: {
                              ...config.filtering.company_size,
                              [category]: { ...range, max: parseInt(e.target.value) || 0 },
                            },
                          },
                        })
                      }
                    />
                    <span className="text-sm text-muted-foreground">employees</span>
                  </div>
                )
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Allowed Categories</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {["startup", "medium", "large", "unknown"].map((cat) => (
                  <label key={cat} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.filtering.allowed_categories.includes(cat)}
                      onChange={(e) => {
                        const cats = config.filtering.allowed_categories;
                        const updated = e.target.checked
                          ? [...cats, cat]
                          : cats.filter((c: string) => c !== cat);
                        setConfig({
                          ...config,
                          filtering: { ...config.filtering, allowed_categories: updated },
                        });
                      }}
                      className="rounded"
                    />
                    <span className="text-sm capitalize">{cat}</span>
                  </label>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Scoring Tab */}
        <TabsContent value="scoring" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">AI Scoring</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="text-sm font-medium block mb-1">Provider</label>
                  <Select
                    value={config.scoring.provider}
                    onValueChange={(v) =>
                      setConfig({
                        ...config,
                        scoring: { ...config.scoring, provider: v },
                      })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="openai">OpenAI</SelectItem>
                      <SelectItem value="anthropic">Anthropic</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-sm font-medium block mb-1">Model</label>
                  <Input
                    value={config.scoring.model}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        scoring: { ...config.scoring, model: e.target.value },
                      })
                    }
                  />
                </div>
              </div>

              <div>
                <label className="text-sm font-medium block mb-1">Min Relevance Score</label>
                <div className="flex items-center gap-3">
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={config.scoring.min_relevance_score}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        scoring: {
                          ...config.scoring,
                          min_relevance_score: parseFloat(e.target.value),
                        },
                      })
                    }
                    className="flex-1"
                  />
                  <span className="text-sm font-mono w-12">
                    {(config.scoring.min_relevance_score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              <div>
                <label className="text-sm font-medium block mb-1">User Profile</label>
                <textarea
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm min-h-[120px] focus:outline-none focus:ring-2 focus:ring-ring"
                  value={config.scoring.user_profile}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      scoring: { ...config.scoring, user_profile: e.target.value },
                    })
                  }
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Rate Limiting Tab */}
        <TabsContent value="rate" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Rate Limiting</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="text-sm font-medium block mb-1">
                    Requests per minute
                  </label>
                  <Input
                    type="number"
                    value={config.rate_limiting.requests_per_minute}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        rate_limiting: {
                          ...config.rate_limiting,
                          requests_per_minute: parseInt(e.target.value) || 10,
                        },
                      })
                    }
                  />
                </div>
                <div>
                  <label className="text-sm font-medium block mb-1">Max retries</label>
                  <Input
                    type="number"
                    value={config.rate_limiting.retry_max}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        rate_limiting: {
                          ...config.rate_limiting,
                          retry_max: parseInt(e.target.value) || 3,
                        },
                      })
                    }
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
