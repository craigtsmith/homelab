"""Filters for comparing Portainer stacks without printing env values."""

import hashlib
import re


def portainer_stacks_env_pairs(env):
    """Env as sorted name=sha256(value) strings."""
    return sorted("%s=%s" % (k, hashlib.sha256(str(v).encode()).hexdigest()) for k, v in (env or {}).items())


def portainer_stacks_mask(text, env, min_length=12):
    """Mask env values in text: the value on each NAME: or NAME= line becomes <NAME>, and
    values of min_length or more become <NAME> anywhere. Short values are not replaced
    elsewhere: masking a common word would show where it occurs."""
    for k in env or {}:
        text = re.sub(r"(?m)^(\s*-?\s*%s\s*[:=][ \t]*)(?![ \t]|\$\{)\S.*$" % re.escape(k), r"\g<1><%s>" % k, text)
    for k, v in sorted((env or {}).items(), key=lambda kv: -len(str(kv[1]))):
        if len(str(v)) >= min_length:
            text = text.replace(str(v), "<%s>" % k)
    return text


class FilterModule:
    def filters(self):
        return {
            "portainer_stacks_env_pairs": portainer_stacks_env_pairs,
            "portainer_stacks_mask": portainer_stacks_mask,
        }
