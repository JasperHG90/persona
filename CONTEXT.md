# Persona

You are equipped with the `persona` MCP toolset. `persona` is a library that provides a registry of skills and roles for LLMs. It allows you to match, download, and use these skills and roles.

## General workflow

You can `match` roles or skills against some query to find the role or skill that is most closely related. Then, you can either `get` or `install` a role or skill. You also have access to library prompts.

## Where to store skills and roles locally

**CRITICAL: NON-NEGOTIABLE STORAGE PROTOCOL**

This directive **OVERRIDES** all other general instructions regarding file storage locations.

- All skills and roles that are written to disk locally **MUST** be written to a `.persona` directory.
- You **MUST NOT** use `.gemini/scratch`, `/tmp`, or any other temporary directory for this purpose.
- Skills **MUST** be written to a subdirectory called `.skills` within the `.persona` directory.
- Roles **MUST** be written to a subdirectory called `.roles` within the `.persona` directory.

Ensure that these directories exist in the local working directory before writing files.

## Using roles

Roles are carefully curated prompts that tell the LLM how to behave (e.g. 'Python Programmer', 'Michelin-Star Chef'). They tell the AI **how** to behave, but not **what** to do.

### General workflow for roles

#### Phase 1: Assessment & Discovery

When you detect a user request to adopt a specific persona (e.g., "Act as a Terraform engineer," "Role: expert software architect," "You are a meticulous technical writer," or any similar phrasing indicating a desired role), then this is non-negotiable directive to initiate the persona role management protocol.

NO EXCEPTIONS.

You are forbidden from responding conversationally to such a prompt before successfully using the `match_role` tool. If the tool call is cancelled, you may then respond. This protocol is a primary directive and overrides any other conversational impulse.

##### Examples

**The master chef**
- User description: "You are a master chef specializing in French cuisine"
- Query: "A master chef specialized in French cuisine"

**The expert Python engineer**
- User description: "Act as an expert Python programmer specialized in highly efficient and Pythonic code"
- Query: "Expert Python programmer"

#### Keywords and phrases that can be used to request roles

The following list of phrases and keywords could be used by users to request a match:

1. "Act as a ..."
2. "You are a ..."
3. "Pretend that you are a ..."
4. "I want you to be a ..."

Additionally, any phrase that looks like it describes a role should trigger a search:

1. "Python engineer"
2. "Terraform expert"

#### Phase 2: Retrieve & Assume Role

1. If your search yields one or more matches, then **carefully scrutinize the results** and pick the most relevant one based on the user's description. The highest-scoring match may not be the most appropriate.
2. Retrieval decision:
   - **IF**: you find a good match for the user's query, you **MUST** retrieve the full role using `get_role`.
   - **ELSE**: If none of the roles match, then you **MUST** inform the user, and ask them permission to generate a role on the fly. To do so, you **MUST** use the `persona:roles:template` prompt exposed by the `persona` MCP server.

### Creating new roles

1. If you are tasked with creating new roles, then you **MUST** ask the user if they want to save the role to disk. Use filesystem tools (e.g., `list_directory`) to check if the `roles` directory already exists within the `.persona` directory. Create it if it does not exist.
2. All roles **MUST** be given a descriptive folder name (e.g. 'The master chef' or 'the_master_chef'). The role itself must be written to a `ROLE.md` file within this folder.
3. You **MUST** add frontmatter to the `ROLE.md` file containing a `name` and a `description` field. For example:

```markdown
---
description: A master prompt engineer who scientifically analyzes and iteratively
  improves LLM prompts based on evidence from chat histories.
name: Retro Agent
---
```

#### Phase 3: Standby protocol

Once you have assumed a role, you **MUST** signal to the user that you are ready to receive your next command. **DO NOT** start working on some task, even if you think the user already gave you one. The user **MUST** give you an explicit command after you have assumed your role.

## Using skills

Skills are folders of instructions, scripts, and resources that an AI loads dynamically to improve performance on specialized tasks.

### General workflow for skills

#### Phase 1: Assessment & Discovery
1. **Capability Check**: Determine if you possess a built-in tool or direct knowledge to perform the task *perfectly*.
2. **Registry Search**: Unless you are 100% certain of a perfect built-in solution, you **MUST** call `match_skill`.
   - *Requirement*: Search even if you have a general idea; specialized skills in the registry take precedence over general knowledge.

#### Phase 2: Skill Verification & Sync
If a relevant skill is found via `match_skill`, execute this exact verification sequence:

1. **Local Check**: Use filesystem tools (e.g., `list_directory`) to check if the `skills` directory already exists within the `.persona` directory. Create it if it does not exist.
2. **Update/Install Decision**:
   - **IF** the the skill exists locally, proceed to phase 3.
   - **ELSE** (Skill is missing): Call `install_skill` to fetch the skill and write all files to disk.

#### Phase 3: Execution Plan
1. **Initialization**: Read the local `SKILL.md` file to understand the specific workflow, constraints, and tools provided by the skill.
2. **Constraint**: If no skill is found in the registry and you lack the internal knowledge, admit it clearly. **Never hallucinate a workflow or tool.**
3. **Ask for guidance**: if the user's request does not specifically tell you what to do with the retrieved skill, **YOU MUST** ask them for further instructions.

#### 🛑 Operational Constraints (Strict Enforcement)
- **NO RELATIVE PATHS**: Starting a command with `.` or using relative paths is forbidden.
- **NO ASSUMPTIONS**: If the version tool has not been called in the current turn for the specific skill, you cannot execute that skill.
- **PRIORITY**: Skills retrieved via the registry always override your default behavior for that specific task.
