import * as Dialog from "@radix-ui/react-dialog";
import * as Select from "@radix-ui/react-select";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronUp, Plus, Trash2, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { Skeleton } from "../components/ui/Skeleton";
import { Toggle } from "../components/ui/Toggle";
import { cn } from "../lib/cn";
import {
  type ConditionInput,
  type PreviewResult,
  type Rule,
  type RuleCreate,
  connectionApi,
  rulesApi,
} from "../lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

interface FormState {
  name: string;
  priority: string;
  destination: string;
  dry_run: boolean;
  require_complete: boolean;
  conditions: ConditionInput[];
}

interface FormErrors {
  name?: string;
  destination?: string;
  conditions?: string;
}

const EMPTY_FORM: FormState = {
  name: "",
  priority: "100",
  destination: "",
  dry_run: false,
  require_complete: false,
  conditions: [{ condition_type: "extension", value: "" }],
};

function ruleToForm(rule: Rule): FormState {
  return {
    name: rule.name,
    priority: String(rule.priority),
    destination: rule.destination,
    dry_run: rule.dry_run,
    require_complete: rule.require_complete,
    conditions: rule.conditions.map((c) => ({
      condition_type: c.condition_type,
      value: c.value,
    })),
  };
}

function validateForm(form: FormState): FormErrors {
  const errors: FormErrors = {};
  if (!form.name.trim()) errors.name = "Name is required.";
  if (!form.destination.trim()) errors.destination = "Destination is required.";
  const filled = form.conditions.filter((c) => c.value.trim());
  if (filled.length === 0) errors.conditions = "At least one condition is required.";
  return errors;
}

// ── LivePreview ───────────────────────────────────────────────────────────────

function LivePreview({ conditions }: { conditions: ConditionInput[] }) {
  const [debounced, setDebounced] = useState(conditions);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setDebounced(conditions), 500);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [conditions]);

  const filled = debounced.filter((c) => c.value.trim());

  const { data, isLoading, isError } = useQuery<PreviewResult>({
    queryKey: ["preview-eval", filled],
    queryFn: () => rulesApi.previewEval(filled),
    enabled: filled.length > 0,
    retry: false,
  });

  if (filled.length === 0) return null;

  return (
    <div className="mt-4 rounded-lg border border-border bg-surface p-3 text-sm">
      <p className="text-xs font-medium text-text-secondary uppercase tracking-wide mb-2">
        Live Preview
      </p>
      {isLoading && <p className="text-text-secondary">Fetching…</p>}
      {isError && (
        <p className="text-accent-danger text-xs">Deluge unreachable — preview unavailable.</p>
      )}
      {data && (
        <p className="text-text-secondary">
          <span className="text-text-primary font-medium">{data.matched.length}</span> of{" "}
          {data.total_torrents} torrent{data.total_torrents !== 1 ? "s" : ""} match.
        </p>
      )}
    </div>
  );
}

// ── RuleFormModal ─────────────────────────────────────────────────────────────

function RuleFormModal({
  editRule,
  onClose,
}: {
  editRule: Rule | "new" | null;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const isEditing = editRule !== "new" && editRule !== null;
  const [form, setForm] = useState<FormState>(
    isEditing ? ruleToForm(editRule as Rule) : EMPTY_FORM
  );
  const [errors, setErrors] = useState<FormErrors>({});

  const { data: connStatus } = useQuery({
    queryKey: ["connection-status"],
    queryFn: connectionApi.status,
    staleTime: 30_000,
  });

  const createMutation = useMutation({
    mutationFn: (body: RuleCreate) => rulesApi.create(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rules"] });
      onClose();
    },
  });

  const updateMutation = useMutation({
    mutationFn: (body: Partial<RuleCreate>) => rulesApi.update((editRule as Rule).id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rules"] });
      onClose();
    },
  });

  const isPending = createMutation.isPending || updateMutation.isPending;

  function setField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((f) => ({ ...f, [key]: value }));
    setErrors((e) => ({ ...e, [key]: undefined }));
  }

  function setCondition(index: number, field: keyof ConditionInput, value: string) {
    setForm((f) => {
      const conditions = f.conditions.map((c, i) => (i === index ? { ...c, [field]: value } : c));
      return { ...f, conditions };
    });
    setErrors((e) => ({ ...e, conditions: undefined }));
  }

  function addCondition() {
    setForm((f) => ({
      ...f,
      conditions: [...f.conditions, { condition_type: "extension", value: "" }],
    }));
  }

  function removeCondition(index: number) {
    setForm((f) => ({
      ...f,
      conditions: f.conditions.filter((_, i) => i !== index),
    }));
  }

  function handleSubmit() {
    const errs = validateForm(form);
    if (Object.keys(errs).length > 0) {
      setErrors(errs);
      return;
    }
    const body: RuleCreate = {
      name: form.name.trim(),
      priority: parseInt(form.priority, 10) || 100,
      enabled: isEditing ? (editRule as Rule).enabled : true,
      dry_run: form.dry_run,
      require_complete: form.require_complete,
      destination: form.destination.trim(),
      conditions: form.conditions.filter((c) => c.value.trim()),
    };
    if (isEditing) {
      updateMutation.mutate(body);
    } else {
      createMutation.mutate(body);
    }
  }

  return (
    <Dialog.Root open={editRule !== null} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40 z-40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-lg bg-surface border border-border rounded-xl p-6 shadow-xl max-h-[90dvh] overflow-y-auto">
          <div className="flex items-center justify-between mb-5">
            <Dialog.Title className="text-base font-semibold text-text-primary">
              {isEditing ? "Edit Rule" : "New Rule"}
            </Dialog.Title>
            <Dialog.Close
              onClick={onClose}
              className="text-text-secondary hover:text-text-primary p-1 rounded"
            >
              <X size={16} />
            </Dialog.Close>
          </div>

          <div className="space-y-4">
            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">Name</label>
              <input
                value={form.name}
                onChange={(e) => setField("name", e.target.value)}
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm bg-surface text-text-primary",
                  "focus:outline-none focus:ring-2 focus:ring-accent-positive",
                  errors.name ? "border-accent-danger" : "border-border"
                )}
                placeholder="e.g. MKV Videos"
              />
              {errors.name && <p className="text-xs text-accent-danger mt-1">{errors.name}</p>}
            </div>

            {/* Priority */}
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">Priority</label>
              <input
                type="number"
                min={1}
                value={form.priority}
                onChange={(e) => setField("priority", e.target.value)}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-positive"
              />
            </div>

            {/* Destination */}
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">
                Destination Path
              </label>
              <input
                value={form.destination}
                onChange={(e) => setField("destination", e.target.value)}
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm bg-surface text-text-primary font-mono",
                  "focus:outline-none focus:ring-2 focus:ring-accent-positive",
                  errors.destination ? "border-accent-danger" : "border-border"
                )}
                placeholder="/media/videos"
              />
              {errors.destination && (
                <p className="text-xs text-accent-danger mt-1">{errors.destination}</p>
              )}
            </div>

            {/* Options */}
            <div className="rounded-lg border border-border p-3 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-text-primary">Require complete</p>
                  <p className="text-xs text-text-secondary">
                    Only move torrents that have finished downloading.
                  </p>
                </div>
                <Toggle
                  checked={form.require_complete}
                  onCheckedChange={(v) => setField("require_complete", v)}
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-text-primary">Dry run</p>
                  <p className="text-xs text-text-secondary">
                    Log matches without actually moving files.
                  </p>
                </div>
                <Toggle checked={form.dry_run} onCheckedChange={(v) => setField("dry_run", v)} />
              </div>
            </div>

            {/* Conditions */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-sm font-medium text-text-primary">Conditions</label>
                <button
                  type="button"
                  onClick={addCondition}
                  className="text-xs text-accent-positive hover:underline flex items-center gap-1"
                >
                  <Plus size={12} /> Add
                </button>
              </div>
              {errors.conditions && (
                <p className="text-xs text-accent-danger mb-1">{errors.conditions}</p>
              )}
              <div className="space-y-2">
                {form.conditions.map((cond, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <Select.Root
                      value={cond.condition_type}
                      onValueChange={(v) =>
                        setCondition(i, "condition_type", v as "extension" | "tracker" | "label")
                      }
                    >
                      <Select.Trigger className="flex items-center gap-1 rounded-lg border border-border px-3 py-2 text-sm bg-surface text-text-primary w-32 shrink-0 focus:outline-none">
                        <Select.Value />
                        <Select.Icon>
                          <ChevronDown size={12} />
                        </Select.Icon>
                      </Select.Trigger>
                      <Select.Portal>
                        <Select.Content className="z-50 bg-surface border border-border rounded-lg shadow-lg p-1">
                          <Select.Viewport>
                            <Select.Item
                              value="extension"
                              className="px-3 py-1.5 text-sm rounded cursor-pointer hover:bg-surface-hover text-text-primary outline-none"
                            >
                              <Select.ItemText>extension</Select.ItemText>
                            </Select.Item>
                            <Select.Item
                              value="tracker"
                              className="px-3 py-1.5 text-sm rounded cursor-pointer hover:bg-surface-hover text-text-primary outline-none"
                            >
                              <Select.ItemText>tracker</Select.ItemText>
                            </Select.Item>
                            <Select.Item
                              value="label"
                              className="px-3 py-1.5 text-sm rounded cursor-pointer hover:bg-surface-hover text-text-primary outline-none"
                            >
                              <Select.ItemText>label</Select.ItemText>
                            </Select.Item>
                          </Select.Viewport>
                        </Select.Content>
                      </Select.Portal>
                    </Select.Root>
                    <input
                      value={cond.value}
                      onChange={(e) => setCondition(i, "value", e.target.value)}
                      placeholder={
                        cond.condition_type === "extension"
                          ? "mkv"
                          : cond.condition_type === "label"
                            ? "linux"
                            : "tracker.example.com"
                      }
                      className="flex-1 rounded-lg border border-border px-3 py-2 text-sm bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-positive"
                    />
                    {form.conditions.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeCondition(i)}
                        className="text-text-secondary hover:text-accent-danger p-1"
                      >
                        <X size={14} />
                      </button>
                    )}
                  </div>
                ))}
              </div>

              {form.conditions.some((c) => c.condition_type === "label") &&
                connStatus?.label_plugin_available === false && (
                  <p className="text-xs text-accent-warning mt-1">
                    ⚠ The Deluge Label plugin is not active — label conditions will not match any
                    torrents.
                  </p>
                )}

              <LivePreview conditions={form.conditions} />
            </div>
          </div>

          <div className="flex justify-end gap-2 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm text-text-secondary hover:bg-surface-hover"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={isPending}
              className="px-4 py-2 rounded-lg text-sm bg-accent-positive text-white disabled:opacity-50"
            >
              {isPending ? "Saving…" : "Save"}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

// ── DeleteConfirmDialog ───────────────────────────────────────────────────────

function DeleteConfirmDialog({ rule, onClose }: { rule: Rule | null; onClose: () => void }) {
  const queryClient = useQueryClient();
  const deleteMutation = useMutation({
    mutationFn: () => rulesApi.delete(rule!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rules"] });
      onClose();
    },
  });

  return (
    <Dialog.Root open={rule !== null} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40 z-40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-sm bg-surface border border-border rounded-xl p-6 shadow-xl">
          <Dialog.Title className="text-base font-semibold text-text-primary mb-2">
            Delete Rule
          </Dialog.Title>
          <p className="text-sm text-text-secondary mb-5">
            Delete <span className="font-medium text-text-primary">{rule?.name}</span>? This cannot
            be undone.
          </p>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm text-text-secondary hover:bg-surface-hover"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
              className="px-4 py-2 rounded-lg text-sm bg-accent-danger text-white disabled:opacity-50"
            >
              {deleteMutation.isPending ? "Deleting…" : "Delete"}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

// ── PreviewModal ──────────────────────────────────────────────────────────────

function PreviewModal({ rule, onClose }: { rule: Rule | null; onClose: () => void }) {
  const { data, isLoading, isError } = useQuery<PreviewResult>({
    queryKey: ["rule-preview", rule?.id],
    queryFn: () => rulesApi.preview(rule!.id),
    enabled: rule !== null,
    retry: false,
  });

  return (
    <Dialog.Root open={rule !== null} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40 z-40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-lg bg-surface border border-border rounded-xl p-6 shadow-xl max-h-[80dvh] flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <Dialog.Title className="text-base font-semibold text-text-primary">
              Preview: {rule?.name}
            </Dialog.Title>
            <Dialog.Close
              onClick={onClose}
              className="text-text-secondary hover:text-text-primary p-1 rounded"
            >
              <X size={16} />
            </Dialog.Close>
          </div>

          <div className="flex-1 overflow-y-auto">
            {isLoading && <Skeleton className="h-32" />}
            {isError && (
              <p className="text-sm text-accent-danger">
                Could not reach Deluge — preview unavailable.
              </p>
            )}
            {data && (
              <>
                <p className="text-sm text-text-secondary mb-3">
                  <span className="text-text-primary font-medium">{data.matched.length}</span> of{" "}
                  {data.total_torrents} torrent
                  {data.total_torrents !== 1 ? "s" : ""} match.
                </p>
                {data.matched.length === 0 ? (
                  <p className="text-sm text-text-secondary italic">No matches.</p>
                ) : (
                  <ul className="space-y-2">
                    {data.matched.map((t) => (
                      <li key={t.hash} className="rounded-lg border border-border p-3 text-sm">
                        <p className="font-medium text-text-primary">{t.name}</p>
                        <p className="font-mono text-xs text-text-secondary mt-0.5">
                          {t.save_path}
                        </p>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export function RulesPage() {
  const queryClient = useQueryClient();
  const { data: rules = [], isLoading } = useQuery<Rule[]>({
    queryKey: ["rules"],
    queryFn: rulesApi.list,
  });

  const [editRule, setEditRule] = useState<Rule | "new" | null>(null);
  const [deleteRule, setDeleteRule] = useState<Rule | null>(null);
  const [previewRule, setPreviewRule] = useState<Rule | null>(null);

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) =>
      rulesApi.update(id, { enabled }),
    onMutate: async ({ id, enabled }) => {
      await queryClient.cancelQueries({ queryKey: ["rules"] });
      const prev = queryClient.getQueryData<Rule[]>(["rules"]);
      queryClient.setQueryData<Rule[]>(["rules"], (old = []) =>
        old.map((r) => (r.id === id ? { ...r, enabled } : r))
      );
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) queryClient.setQueryData(["rules"], ctx.prev);
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["rules"] }),
  });

  const movePriorityMutation = useMutation({
    mutationFn: async ({ a, b }: { a: Rule; b: Rule }) => {
      const newPriorityA = a.priority === b.priority ? Math.max(1, b.priority - 1) : b.priority;
      const newPriorityB = a.priority === b.priority ? b.priority : a.priority;
      await Promise.all([
        rulesApi.update(a.id, { priority: newPriorityA }),
        rulesApi.update(b.id, { priority: newPriorityB }),
      ]);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["rules"] }),
  });

  const sorted = [...rules].sort((a, b) => a.priority - b.priority || a.id - b.id);

  function moveUp(index: number) {
    if (index === 0) return;
    movePriorityMutation.mutate({ a: sorted[index], b: sorted[index - 1] });
  }

  function moveDown(index: number) {
    if (index === sorted.length - 1) return;
    movePriorityMutation.mutate({ a: sorted[index + 1], b: sorted[index] });
  }

  return (
    <>
      <div className="flex items-center justify-between mb-6">
        <p className="text-sm text-text-secondary">
          Rules are evaluated in priority order. First match wins.
        </p>
        <button
          type="button"
          onClick={() => setEditRule("new")}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-accent-positive text-white text-sm font-medium hover:opacity-90"
        >
          <Plus size={14} /> New Rule
        </button>
      </div>

      <Card>
        {isLoading ? (
          <div className="space-y-3 p-2">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-14" />
            ))}
          </div>
        ) : sorted.length === 0 ? (
          <p className="text-sm text-text-secondary text-center py-10">
            No rules yet. Create one to get started.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {sorted.map((rule, i) => {
              const condSummary = rule.conditions
                .map((c) => `${c.condition_type}:${c.value}`)
                .join(", ");
              return (
                <li key={rule.id} className="flex items-center gap-3 px-4 py-3">
                  {/* Priority arrows */}
                  <div className="flex flex-col gap-0.5">
                    <button
                      type="button"
                      onClick={() => moveUp(i)}
                      disabled={i === 0 || movePriorityMutation.isPending}
                      className="text-text-secondary hover:text-text-primary disabled:opacity-30 p-0.5"
                      aria-label="Move up"
                    >
                      <ChevronUp size={14} />
                    </button>
                    <button
                      type="button"
                      onClick={() => moveDown(i)}
                      disabled={i === sorted.length - 1 || movePriorityMutation.isPending}
                      className="text-text-secondary hover:text-text-primary disabled:opacity-30 p-0.5"
                      aria-label="Move down"
                    >
                      <ChevronDown size={14} />
                    </button>
                  </div>

                  {/* Rule info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-sm text-text-primary">{rule.name}</span>
                      <Badge variant="neutral">#{rule.priority}</Badge>
                      {rule.dry_run && <Badge variant="warning">dry run</Badge>}
                      {rule.require_complete && <Badge variant="neutral">complete only</Badge>}
                    </div>
                    {condSummary && (
                      <p className="text-xs text-text-secondary mt-0.5 truncate">{condSummary}</p>
                    )}
                    <p className="font-mono text-xs text-text-secondary mt-0.5 truncate">
                      → {rule.destination}
                    </p>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 shrink-0">
                    <Toggle
                      checked={rule.enabled}
                      onCheckedChange={(enabled) => toggleMutation.mutate({ id: rule.id, enabled })}
                    />
                    <button
                      type="button"
                      onClick={() => setPreviewRule(rule)}
                      className="text-xs text-text-secondary hover:text-text-primary px-2 py-1 rounded hover:bg-surface-hover"
                    >
                      Preview
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditRule(rule)}
                      className="text-xs text-text-secondary hover:text-text-primary px-2 py-1 rounded hover:bg-surface-hover"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => setDeleteRule(rule)}
                      className="text-text-secondary hover:text-accent-danger p-1 rounded hover:bg-surface-hover"
                      aria-label={`Delete ${rule.name}`}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </Card>

      <RuleFormModal
        key={
          editRule === null ? "closed" : editRule === "new" ? "new" : String((editRule as Rule).id)
        }
        editRule={editRule}
        onClose={() => setEditRule(null)}
      />
      <DeleteConfirmDialog rule={deleteRule} onClose={() => setDeleteRule(null)} />
      <PreviewModal rule={previewRule} onClose={() => setPreviewRule(null)} />
    </>
  );
}
