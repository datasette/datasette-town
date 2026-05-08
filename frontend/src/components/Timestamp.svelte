<script lang="ts">
  interface Props {
    value: string;
    prefix?: string;
  }

  let { value, prefix = "" }: Props = $props();

  function formatUtcTimestamp(ts: string): string {
    // SQLite timestamps are UTC but lack a Z suffix — add it so JS parses as UTC
    let normalized = ts.trim();
    if (
      !normalized.endsWith("Z") &&
      !normalized.includes("+") &&
      !normalized.includes("-", 10)
    ) {
      normalized += "Z";
    }
    const date = new Date(normalized);
    if (isNaN(date.getTime())) return ts;

    const months = [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ];
    const month = months[date.getMonth()];
    const day = date.getDate();
    let hours = date.getHours();
    const minutes = date.getMinutes();
    const ampm = hours >= 12 ? "pm" : "am";
    hours = hours % 12 || 12;
    const minStr = minutes < 10 ? `0${minutes}` : `${minutes}`;
    return `${month} ${day} ${hours}:${minStr}${ampm}`;
  }
</script>

<span title={value}>{prefix}{formatUtcTimestamp(value)}</span>
