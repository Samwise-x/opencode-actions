const secretName = /(TOKEN|SECRET|PASSWORD|CREDENTIAL|API_KEY|ACCESS_KEY|PRIVATE_KEY|AUTH)/i

const forbidden = [
  /(^|[;&|()]\s*)(?:command\s+)?(?:\/(?:usr\/)?bin\/)?gh\s/i,
  /(^|[;&|()]\s*)(?:command\s+)?(?:\/(?:usr\/)?bin\/)?git\s+(push|commit|reset|clean|checkout|switch|rebase|merge|config|remote)\b/i,
  /(^|[;&|()]\s*)sudo\s/i,
  /(^|[;&|()]\s*)(nohup|setsid|crontab|systemctl)\s/i,
]

export const HardenRuntime = async () => ({
  "shell.env": async (_input, output) => {
    for (const name of Object.keys(process.env)) {
      if (secretName.test(name)) output.env[name] = ""
    }
  },

  "tool.execute.before": async (input, output) => {
    if (input.tool !== "bash") return
    const command = String(output.args?.command ?? "")
    if (forbidden.some((rule) => rule.test(command))) {
      throw new Error("command rejected by repository-owned OpenCode runtime guard")
    }
  },
})
