// Inbox channel adapters (PRD-006 B). Interface thống nhất; placeholder, KHÔNG credential.
// Mỗi adapter: { key, label, configured, fetchMessages(all) } — hiện lọc từ mock chung.

const CFG = (typeof window !== "undefined" && window.OMI_CONFIG) || {};

function makeAdapter(key, label) {
  return {
    key,
    label,
    // configured chỉ true khi có cấu hình runtime (không hardcode secret).
    configured: Boolean((CFG.CHANNELS || {})[key]),
    async fetchMessages(all) {
      return all.filter((m) => m.channel === key);
    },
  };
}

export const ADAPTERS = [
  makeAdapter("telegram", "Telegram"),
  makeAdapter("email", "Email"),
  makeAdapter("zalo_oa", "Zalo OA"),
  makeAdapter("facebook_messenger", "Facebook"),
];

export async function loadAll() {
  const res = await fetch("mock/messages.json");
  return res.json();
}
