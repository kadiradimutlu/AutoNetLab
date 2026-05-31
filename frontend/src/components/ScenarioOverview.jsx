import MessageBox from "./MessageBox";
import {
  formatDifficulty,
  formatStatus,
  getDifficultyClass
} from "../utils/formatters";

const CAMPUS_SCENARIO_ID = "campus-core-routing";
const CAMPUS_NODE_IDS = ["client1", "client2", "srl1", "srl2", "srl3", "srl4"];

const DEFAULT_TOPIC_LABELS = {
  easy: ["IP Addressing", "Interface Status"],
  medium: ["IP Addressing", "Routing", "Connectivity"],
  hard: ["IP Addressing", "Routing", "Interface Status", "ACL", "Multi-step Troubleshooting"]
};

const DEFAULT_STUDENT_HINTS = [
  "Check IP addressing and subnet masks.",
  "Verify interface status before testing connectivity.",
  "Review routing and default gateway configuration.",
  "Compare addressing, interfaces, and routing step by step across the topology."
];

const CAMPUS_TROUBLESHOOTING_STEPS = [
  "Identify the client edge segments and their default gateways.",
  "Verify SR Linux subinterfaces on the client-facing and core-facing links.",
  "Inspect static routes across the upper and lower core paths.",
  "Test client-to-client reachability after confirming gateway and route state."
];

function normalizeList(value) {
  if (!value) {
    return [];
  }

  if (Array.isArray(value)) {
    return value.filter(Boolean);
  }

  return [value];
}

function hasRichScenarioFields(scenario) {
  return Boolean(
    scenario?.objective ||
      scenario?.story ||
      scenario?.devices ||
      scenario?.addressing_table ||
      scenario?.routing_requirements ||
      scenario?.expected_connectivity ||
      scenario?.student_tasks ||
      scenario?.student_notes
  );
}

function getScenarioSource(labSession) {
  const scenario = labSession?.scenario || labSession?.scenario_metadata || {};
  const overview = labSession?.scenario_overview || {};

  if (hasRichScenarioFields(scenario)) {
    return scenario;
  }

  return overview || scenario || labSession?.metadata || {};
}

function getTopics(labSession) {
  const scenario = getScenarioSource(labSession);
  const explicitTopics = normalizeList(
    scenario.topics ||
      scenario.topic_focus ||
      scenario.focus_topics ||
      labSession?.topics ||
      labSession?.topic_focus
  );

  if (explicitTopics.length > 0) {
    return explicitTopics;
  }

  return DEFAULT_TOPIC_LABELS[String(labSession?.difficulty || "easy").toLowerCase()] || DEFAULT_TOPIC_LABELS.easy;
}

function getHints(labSession) {
  const scenario = getScenarioSource(labSession);
  const hints = normalizeList(scenario.hints || labSession?.hints);

  return hints.length > 0 ? hints : DEFAULT_STUDENT_HINTS;
}

function getScenarioTitle(labSession) {
  const scenario = getScenarioSource(labSession);

  return scenario.title || scenario.name || "Scenario Overview";
}

function getScenarioDescription(labSession) {
  const scenario = getScenarioSource(labSession);

  if (scenario.summary || scenario.description) {
    return scenario.summary || scenario.description;
  }

  const difficulty = String(labSession?.difficulty || "easy").toLowerCase();

  if (difficulty === "hard") {
    return "This hard scenario combines multiple troubleshooting topics. Work through the topology carefully and validate only after checking each device.";
  }

  if (difficulty === "medium") {
    return "This medium scenario includes more than one issue area. Use the topology, CLI access, and general hints to narrow down the problem.";
  }

  return "This scenario focuses on basic troubleshooting steps and validation feedback.";
}

function getSafeText(value, fallback = "-") {
  if (value === undefined || value === null || value === "") {
    return fallback;
  }

  return String(value);
}

function getDeviceLabel(device) {
  return device?.label || device?.id || device?.name || "Device";
}

function toReadableLabel(value, fallback = "Unknown") {
  const safeValue = getSafeText(value, fallback);

  return safeValue
    .replace(/[_-]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function getDeviceRole(device) {
  const rawRole = String(device?.role || device?.kind || device?.type || "device").toLowerCase();
  const rawLabel = String(device?.label || device?.id || "").toLowerCase();

  if (rawRole.includes("client") || rawLabel.includes("client")) {
    return "client";
  }

  if (rawRole.includes("edge")) {
    return "edge_router";
  }

  if (rawRole.includes("core")) {
    return "core_router";
  }

  if (rawRole.includes("router") || rawLabel.includes("router") || rawLabel.startsWith("srl")) {
    return "router";
  }

  return rawRole || "device";
}

function getDeviceRoleLabel(device) {
  const role = getDeviceRole(device);

  if (role === "client") {
    return "Client";
  }

  if (role === "edge_router") {
    return "Edge Router";
  }

  if (role === "core_router") {
    return "Core Router";
  }

  if (role === "router") {
    return "Router";
  }

  return toReadableLabel(role, "Device");
}

function getRoleClassName(device) {
  const role = getDeviceRole(device);

  if (role === "client") {
    return "client";
  }

  if (role === "edge_router") {
    return "edge";
  }

  if (role === "core_router") {
    return "core";
  }

  if (role === "router") {
    return "router";
  }

  return "device";
}

function getScenarioIdentity(scenario, labSession) {
  return [
    scenario?.id,
    scenario?.scenario_id,
    scenario?.topology_template,
    scenario?.title,
    scenario?.name,
    labSession?.scenario_id,
    labSession?.topology_template,
    labSession?.topology?.name
  ]
    .filter(Boolean)
    .map((item) => String(item).toLowerCase())
    .join(" ");
}

function isCampusScenario(scenario, labSession, devices) {
  const identity = getScenarioIdentity(scenario, labSession);
  const deviceIds = new Set(
    devices
      .map((device) => String(device?.id || device?.name || "").toLowerCase())
      .filter(Boolean)
  );
  const hasCampusDevices = CAMPUS_NODE_IDS.every((nodeId) => deviceIds.has(nodeId));

  return identity.includes(CAMPUS_SCENARIO_ID) || identity.includes("campus") || hasCampusDevices;
}

function ipv4ToNumber(address) {
  const octets = String(address || "").split(".").map((part) => Number(part));

  if (octets.length !== 4 || octets.some((part) => Number.isNaN(part) || part < 0 || part > 255)) {
    return null;
  }

  return octets.reduce((result, octet) => ((result << 8) + octet) >>> 0, 0);
}

function numberToIpv4(value) {
  return [24, 16, 8, 0].map((shift) => (value >>> shift) & 255).join(".");
}

function getNetworkFromCidr(value) {
  const [address, prefixText] = String(value || "").split("/");
  const prefix = Number(prefixText);
  const addressNumber = ipv4ToNumber(address);

  if (addressNumber === null || Number.isNaN(prefix) || prefix < 0 || prefix > 32) {
    return "-";
  }

  const mask = prefix === 0 ? 0 : (0xffffffff << (32 - prefix)) >>> 0;
  const networkNumber = addressNumber & mask;

  return `${numberToIpv4(networkNumber)}/${prefix}`;
}

function getClientAddressRows(addressingTable) {
  return addressingTable.filter((row) => {
    const device = String(row?.device || "").toLowerCase();
    const role = String(row?.role || "").toLowerCase();

    return device.includes("client") || Boolean(row?.default_gateway) || role.includes("client");
  });
}

function getAddressingRowNetwork(row) {
  const network = getNetworkFromCidr(row?.ip_address);

  return network === "-" ? "Network unavailable" : network;
}

function formatConnectivityPath(item) {
  const source = getSafeText(item?.source, "Source");
  const destination = getSafeText(item?.destination, "Destination");

  return `${source} <-> ${destination}`;
}

function ScenarioDataTable({ columns, rows, emptyMessage }) {
  if (!rows.length) {
    return (
      <div className="scenario-empty-state">
        <p>{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="scenario-table-scroll">
      <table className="scenario-data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key}>{column.label}</th>
            ))}
          </tr>
        </thead>

        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`${row.device || row.source || "row"}-${rowIndex}`}>
              {columns.map((column) => (
                <td key={column.key}>{getSafeText(row[column.key])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ScenarioAddressingTable({ rows }) {
  if (!rows.length) {
    return (
      <div className="scenario-empty-state">
        <p>No addressing requirements are available.</p>
      </div>
    );
  }

  return (
    <div className="scenario-table-scroll scenario-table-scroll-polished">
      <table className="scenario-data-table scenario-addressing-table">
        <thead>
          <tr>
            <th>Device</th>
            <th>Interface</th>
            <th>IP Address</th>
            <th>Network</th>
            <th>Default Gateway</th>
            <th>Peer</th>
          </tr>
        </thead>

        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`${row.device || "address"}-${row.interface || rowIndex}`}>
              <td>
                <strong>{getSafeText(row.device)}</strong>
                {row.role && <small>{row.role}</small>}
              </td>
              <td><code>{getSafeText(row.interface)}</code></td>
              <td><code>{getSafeText(row.ip_address)}</code></td>
              <td><span className="scenario-network-pill">{getAddressingRowNetwork(row)}</span></td>
              <td>{row.default_gateway ? <code>{row.default_gateway}</code> : <span className="muted">Router interface</span>}</td>
              <td>{getSafeText(row.connects_to)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ScenarioRequirementCards({ requirements }) {
  if (!requirements.length) {
    return (
      <div className="scenario-empty-state">
        <p>No routing requirements are available.</p>
      </div>
    );
  }

  return (
    <div className="scenario-requirement-card-grid">
      {requirements.map((item, index) => (
        <article className="scenario-requirement-card" key={`${item?.device || "requirement"}-${index}`}>
          <span className="scenario-step-number">{index + 1}</span>
          <div>
            <strong>{getSafeText(item?.device, "Device")}</strong>
            <p>{getSafeText(item?.requirement || item?.description || item)}</p>
          </div>
        </article>
      ))}
    </div>
  );
}

function ScenarioConnectivityCards({ connectivity }) {
  if (!connectivity.length) {
    return (
      <div className="scenario-empty-state">
        <p>No expected connectivity checks are available.</p>
      </div>
    );
  }

  return (
    <div className="scenario-connectivity-grid">
      {connectivity.map((item, index) => (
        <article className="scenario-connectivity-card" key={`${item?.source || "source"}-${item?.destination || "destination"}-${index}`}>
          <div className="scenario-connectivity-path">{formatConnectivityPath(item)}</div>
          <div className="scenario-connectivity-meta">
            <span>{getSafeText(item?.protocol, "Protocol")}</span>
            <span>Expected</span>
          </div>
          <p>{getSafeText(item?.expectation || item?.description || item)}</p>
        </article>
      ))}
    </div>
  );
}

function CampusGuidancePanel({ devices, addressingTable, expectedConnectivity }) {
  const clientRows = getClientAddressRows(addressingTable);
  const clientDevices = devices.filter((device) => getDeviceRole(device) === "client");
  const edgeRouters = devices.filter((device) => getDeviceRole(device) === "edge_router");
  const coreRouters = devices.filter((device) => getDeviceRole(device) === "core_router");

  return (
    <div className="scenario-campus-guidance-panel">
      <div className="section-title-row compact">
        <div>
          <h4>Campus Guidance</h4>
          <p className="muted">
            Start from the client edge networks, confirm the gateways, inspect SR Linux routes, and then test end-to-end connectivity.
          </p>
        </div>

        <span className="badge neutral">Campus Core</span>
      </div>

      <div className="scenario-guidance-summary-grid">
        <article className="scenario-guidance-card">
          <span>Client Edge Networks</span>
          <div className="scenario-guidance-list">
            {clientRows.length === 0 && <p className="muted">Client addressing metadata is not available.</p>}
            {clientRows.map((row) => (
              <div key={`${row.device}-${row.interface}`}>
                <strong>{getSafeText(row.device)}</strong>
                <p>
                  {getAddressingRowNetwork(row)} - gateway {getSafeText(row.default_gateway, "not provided")}
                </p>
              </div>
            ))}
          </div>
        </article>

        <article className="scenario-guidance-card">
          <span>Device Roles</span>
          <div className="scenario-role-summary-grid">
            <div>
              <strong>{clientDevices.length}</strong>
              <small>Clients</small>
            </div>
            <div>
              <strong>{edgeRouters.length}</strong>
              <small>Edge routers</small>
            </div>
            <div>
              <strong>{coreRouters.length}</strong>
              <small>Core routers</small>
            </div>
          </div>
        </article>

        <article className="scenario-guidance-card">
          <span>Connectivity Target</span>
          <div className="scenario-guidance-list">
            {expectedConnectivity.length === 0 && <p className="muted">Connectivity metadata is not available.</p>}
            {expectedConnectivity.map((item, index) => (
              <div key={`${item?.source || "source"}-${item?.destination || "destination"}-${index}`}>
                <strong>{formatConnectivityPath(item)}</strong>
                <p>{getSafeText(item?.protocol, "Protocol")} - {getSafeText(item?.expectation || item?.description)}</p>
              </div>
            ))}
          </div>
        </article>
      </div>

      <div className="scenario-campus-flow">
        {CAMPUS_TROUBLESHOOTING_STEPS.map((step, index) => (
          <article key={step}>
            <span>{index + 1}</span>
            <p>{step}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

function ScenarioDeviceCard({ device, index }) {
  return (
    <article className={`scenario-device-card scenario-device-card-polished role-${getRoleClassName(device)}`} key={`${device?.id || "device"}-${index}`}>
      <div className="scenario-device-card-header">
        <strong>{getDeviceLabel(device)}</strong>
        <span className={`scenario-role-badge ${getRoleClassName(device)}`}>{getDeviceRoleLabel(device)}</span>
      </div>
      <div className="scenario-device-meta">
        <span>{getSafeText(device?.id || device?.name, "device")}</span>
        <span>{getSafeText(device?.os || device?.kind, "Network OS")}</span>
      </div>
      <p>{getSafeText(device?.image, "Image metadata unavailable")}</p>
    </article>
  );
}

function ScenarioOverview({ labSession, t }) {
  if (!labSession) {
    return null;
  }

  const scenario = getScenarioSource(labSession);
  const difficultyClass = getDifficultyClass(labSession.difficulty);
  const topics = getTopics(labSession);
  const hints = getHints(labSession);
  const devices = normalizeList(scenario.devices);
  const addressingTable = normalizeList(scenario.addressing_table);
  const routingRequirements = normalizeList(scenario.routing_requirements);
  const expectedConnectivity = normalizeList(scenario.expected_connectivity);
  const studentTasks = normalizeList(scenario.student_tasks);
  const studentNotes = normalizeList(scenario.student_notes);
  const hasScenarioDesign =
    hasRichScenarioFields(scenario) ||
    devices.length > 0 ||
    addressingTable.length > 0 ||
    routingRequirements.length > 0 ||
    expectedConnectivity.length > 0 ||
    studentTasks.length > 0 ||
    studentNotes.length > 0;
  const isCampus = isCampusScenario(scenario, labSession, devices);

  return (
    <section className={`scenario-overview scenario-overview-polished ${isCampus ? "scenario-overview-campus" : ""}`}>
      <MessageBox
        type="info"
        title="Student View"
        message="Injected faults are intentionally hidden. Use the design requirements, topology, CLI access, and validation feedback as the expected state."
      />

      <div className="scenario-design-hero">
        <div>
          <span className="scenario-eyebrow">Scenario Design Guide</span>
          <h4>{getScenarioTitle(labSession)}</h4>
          <p>{getScenarioDescription(labSession)}</p>
        </div>

        <span className={`badge ${difficultyClass}`}>
          {formatDifficulty(labSession.difficulty, t)}
        </span>
      </div>

      <div className="scenario-meta-grid scenario-meta-grid-enhanced">
        <div>
          <span className="muted">Session Status</span>
          <strong>{formatStatus(labSession.status, t)}</strong>
        </div>

        <div>
          <span className="muted">Devices</span>
          <strong>{devices.length || "-"}</strong>
        </div>

        <div>
          <span className="muted">Visible Topics</span>
          <strong>{topics.length}</strong>
        </div>

        <div>
          <span className="muted">Learning Mode</span>
          <strong>Enabled</strong>
        </div>
      </div>

      {topics.length > 0 && (
        <div className="topic-pill-list">
          {topics.map((topic, index) => (
            <span className="topic-pill" key={`${topic}-${index}`}>
              {String(topic).replace(/_/g, " ")}
            </span>
          ))}
        </div>
      )}

      {isCampus && (
        <CampusGuidancePanel
          devices={devices}
          addressingTable={addressingTable}
          expectedConnectivity={expectedConnectivity}
        />
      )}

      {hasScenarioDesign && (
        <div className="scenario-detail-grid scenario-detail-grid-polished">
          {scenario.objective && (
            <div className="scenario-detail-card scenario-detail-card-wide scenario-highlight-card">
              <h4>Objective</h4>
              <p>{scenario.objective}</p>
            </div>
          )}

          {scenario.story && (
            <div className="scenario-detail-card scenario-detail-card-wide scenario-highlight-card">
              <h4>Design Requirements</h4>
              <p>{scenario.story}</p>
            </div>
          )}

          {devices.length > 0 && (
            <div className="scenario-detail-card scenario-detail-card-wide">
              <div className="section-title-row compact">
                <div>
                  <h4>Devices</h4>
                  <p className="muted">Device roles and operating systems for this scenario.</p>
                </div>
              </div>

              <div className="scenario-device-grid scenario-device-grid-polished">
                {devices.map((device, index) => (
                  <ScenarioDeviceCard device={device} index={index} key={`${device?.id || "device"}-${index}`} />
                ))}
              </div>
            </div>
          )}

          {addressingTable.length > 0 && (
            <div className="scenario-detail-card scenario-detail-card-wide">
              <div className="section-title-row compact">
                <div>
                  <h4>Addressing Table</h4>
                  <p className="muted">Use these addresses and gateways as the expected network state.</p>
                </div>
              </div>
              <ScenarioAddressingTable rows={addressingTable} />
            </div>
          )}

          {routingRequirements.length > 0 && (
            <div className="scenario-detail-card">
              <h4>Routing Requirements</h4>
              <ScenarioRequirementCards requirements={routingRequirements} />
            </div>
          )}

          {expectedConnectivity.length > 0 && (
            <div className="scenario-detail-card">
              <h4>Expected Connectivity</h4>
              <ScenarioConnectivityCards connectivity={expectedConnectivity} />
            </div>
          )}

          {studentTasks.length > 0 && (
            <div className="scenario-detail-card">
              <h4>Student Tasks</h4>
              <ol className="scenario-task-list scenario-task-list-polished">
                {studentTasks.map((task, index) => (
                  <li key={`${task}-${index}`}>
                    <span>{index + 1}</span>
                    <p>{task}</p>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {studentNotes.length > 0 && (
            <div className="scenario-detail-card">
              <h4>Student Notes</h4>
              <ul className="scenario-note-list scenario-note-list-polished">
                {studentNotes.map((note, index) => (
                  <li key={`${note}-${index}`}>{note}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <h4>General Hints</h4>
      <div className="hints-list">
        {hints.map((hint, index) => (
          <div className="hint-item" key={`${hint}-${index}`}>
            <span className="hint-number">{index + 1}</span>
            <p>{hint}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default ScenarioOverview;
