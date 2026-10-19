export interface Paginated<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface User {
  id: string;
  email: string;
  name: string;
}

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  phone?: string | null;
  location?: string | null;
  portfolio_url?: string | null;
  github_url?: string | null;
  linkedin_url?: string | null;
  summary?: string | null;
  technologies: string[];
  experience: unknown[];
  education: unknown[];
  languages: unknown[];
  portfolio_projects: unknown[];
  preferred_application_language: string;
  tone_preference: string;
}

export interface SearchProfile {
  id: string;
  name: string;
  enabled: boolean;
  locations: string[];
  job_titles: Record<string, string[]>;
  technologies: string[];
  employment_types: string[];
  remote_preferences: string[];
  minimum_salary?: number | null;
  preferred_salary_min?: number | null;
  preferred_salary_max?: number | null;
  salary_currency: string;
  hourly_rate_min?: number | null;
  seniority: string[];
  exclusion_rules: unknown[];
  matching_threshold: number;
  auto_apply_enabled: boolean;
  weight_technology: number;
  weight_seniority: number;
  weight_location: number;
  weight_compensation: number;
  weight_other: number;
}

export interface Resume {
  id: string;
  name: string;
  original_filename: string;
  content_type: string;
  version: number;
  is_default: boolean;
  enabled: boolean;
  target_roles: string[];
  file_hash: string;
}

export interface JobMatch {
  id: string;
  overall_score: number;
  skill_score: number;
  seniority_score: number;
  location_score: number;
  compensation_score: number;
  other_score: number;
  decision: string;
  explanation_json: Record<string, unknown>;
  missing_skills_json: string[];
  evaluated_at: string;
}

export interface Job {
  id: string;
  title: string;
  company_name?: string | null;
  company?: { id: string; name: string; website?: string | null } | null;
  location?: string | null;
  remote_type?: string | null;
  employment_type?: string | null;
  seniority?: string | null;
  salary_min?: number | null;
  salary_max?: number | null;
  currency?: string | null;
  salary_period?: string | null;
  original_salary_text?: string | null;
  salary_flag?: string | null;
  technologies: string[];
  source_url?: string | null;
  apply_url?: string | null;
  apply_method?: string | null;
  apply_capabilities?: Record<string, unknown>;
  requirements_json?: Record<string, unknown>;
  status: string;
  description?: string | null;
  published_at?: string | null;
  discovered_at?: string | null;
  contact_email?: string | null;
  match_score?: number | null;
  match_decision?: string | null;
  source?: { id: string; name: string; provider: string } | null;
  match?: JobMatch | null;
  matches?: Array<JobMatch | Record<string, unknown>>;
}

export interface JobSource {
  id: string;
  name: string;
  provider: string;
  source_url?: string | null;
  configuration: Record<string, unknown>;
  enabled: boolean;
  poll_interval_minutes: number;
  last_checked_at?: string | null;
  last_success_at?: string | null;
  health_status: string;
  last_error?: string | null;
  discovered_jobs_count: number;
  apply_capabilities_note?: string | null;
}

export interface Application {
  id: string;
  job_id: string;
  resume_id?: string | null;
  status: string;
  apply_method: string;
  generated_subject?: string | null;
  generated_message?: string | null;
  approved_subject?: string | null;
  approved_message?: string | null;
  recipient_email?: string | null;
  language: string;
  matching_explanation?: Record<string, unknown>;
  generation_metadata?: Record<string, unknown>;
  submission_logs?: unknown[];
  sent_at?: string | null;
  confirmed_at?: string | null;
  last_activity_at?: string;
  failure_reason?: string | null;
  created_at?: string;
  evidence?: Array<{
    id: string;
    claim: string;
    verification_status: string;
    source_chunk_id?: string | null;
    source_document_id?: string | null;
  }>;
  job?: Job | null;
  job_title?: string | null;
  company_name?: string | null;
  salary_min?: number | null;
  salary_max?: number | null;
  currency?: string | null;
}

export interface EmailAccount {
  id: string;
  provider: string;
  email_address: string;
  imap_host: string;
  imap_port: number;
  smtp_host: string;
  smtp_port: number;
  imap_enabled: boolean;
  smtp_enabled: boolean;
  last_sync_at?: string | null;
  allow_llm_processing: boolean;
  connected: boolean;
}

export interface EmailMessage {
  id: string;
  account_id: string;
  message_id: string;
  thread_identifier?: string | null;
  sender: string;
  recipients: string[];
  subject?: string | null;
  text_body?: string | null;
  html_body?: string | null;
  received_at?: string | null;
  sent_at?: string | null;
  classification: string;
  classification_confidence: number;
  related_application_id?: string | null;
  folder?: string | null;
}

export interface EmailThread {
  thread_identifier: string;
  subject?: string | null;
  participants: string[];
  last_message_at?: string | null;
  classification?: string | null;
  related_application_id?: string | null;
  message_count: number;
  messages?: EmailMessage[];
}

export interface KnowledgeDocument {
  id: string;
  title: string;
  document_type: string;
  source: string;
  scope: string;
  checksum: string;
  approved: boolean;
  indexed_at?: string | null;
  metadata_json: Record<string, unknown>;
  embedding_model?: string | null;
  created_at?: string;
  chunk_count?: number;
}

export interface RagDebugResult {
  question: string;
  chunks: Array<{
    id: string;
    content: string;
    score?: number;
    similarity?: number;
    rerank_score?: number | null;
    document_id?: string;
    document_title?: string;
    section_heading?: string | null;
  }>;
  generated_response?: string | null;
  latency_ms?: number | null;
  sources?: string[];
}

export interface AnalyticsOverview {
  jobs_discovered: number;
  jobs_relevant: number;
  applications_drafted: number;
  applications_sent: number;
  employer_responses: number;
  interviews: number;
  average_match_score?: number | null;
  response_rate?: number | null;
}

export interface AnalyticsSeriesPoint {
  date: string;
  applications?: number;
  responses?: number;
  interviews?: number;
  value?: number;
}

export interface AnalyticsFunnelStep {
  stage: string;
  count: number;
}

export interface LlmCostSummary {
  total_tokens: number;
  estimated_cost_usd: number;
  by_operation?: Array<{ operation: string; total_tokens: number; estimated_cost_usd: number }>;
}

export interface AutomationRun {
  id: string;
  job_type: string;
  started_at: string;
  completed_at?: string | null;
  status: string;
  processed_count: number;
  success_count: number;
  error_count: number;
  logs: unknown[];
}

export interface AuditEvent {
  id: string;
  event_type: string;
  entity_type?: string | null;
  entity_id?: string | null;
  timestamp: string;
  metadata_json: Record<string, unknown>;
}

export interface AppSettings {
  key?: string;
  privacy?: {
    allow_llm_email_processing?: boolean;
    store_email_bodies?: boolean;
    redact_pii_in_logs?: boolean;
    allow_llm_on_historical_mail?: boolean;
  };
  email?: {
    dry_run?: boolean;
    sending_enabled?: boolean;
  };
  automation?: {
    enabled?: boolean;
    discover_interval_hours?: number;
  };
  runtime?: {
    email_dry_run?: boolean;
    email_sending_enabled?: boolean;
    llm_configured?: boolean;
    llm_chat_model?: string;
    llm_embedding_model?: string;
    daily_send_limit?: number;
    llm_monthly_budget_usd?: number;
  };
}

export interface MessageOut {
  message: string;
}
