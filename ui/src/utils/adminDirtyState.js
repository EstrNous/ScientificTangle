function normalizeUser(user) {
  return {
    id: user.id,
    role: user.role,
    active: Boolean(user.active ?? user.is_active),
  };
}

function normalizePolicy(policy) {
  return {
    id: policy.id ?? policy.documentId ?? policy.document_id,
    level: policy.level,
    exportAllowed: Boolean(policy.exportAllowed ?? policy.export_allowed),
    roles: [...(policy.roles ?? [])].sort(),
  };
}

export function buildAdminBaselines(users, policies) {
  return {
    users: users.map(normalizeUser),
    policies: policies.map(normalizePolicy),
  };
}

export function isUserDirty(user, baselineUsers) {
  const baseline = baselineUsers.find((item) => item.id === user.id);
  if (!baseline) return true;
  const current = normalizeUser(user);
  return current.role !== baseline.role || current.active !== baseline.active;
}

export function isPolicyDirty(policy, baselinePolicies) {
  const id = policy.id ?? policy.documentId ?? policy.document_id;
  const baseline = baselinePolicies.find((item) => item.id === id);
  if (!baseline) return true;
  const current = normalizePolicy(policy);
  return (
    current.level !== baseline.level
    || current.exportAllowed !== baseline.exportAllowed
    || current.roles.join(',') !== baseline.roles.join(',')
  );
}

export function listDirtyUserIds(users, baselineUsers) {
  return users.filter((user) => isUserDirty(user, baselineUsers)).map((user) => user.id);
}

export function listDirtyPolicyIds(policies, baselinePolicies) {
  return policies
    .filter((policy) => isPolicyDirty(policy, baselinePolicies))
    .map((policy) => policy.id ?? policy.documentId ?? policy.document_id);
}
