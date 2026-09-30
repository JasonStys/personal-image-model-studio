"""Closed, bounded application contracts. Fields describe inputs, not promised model abilities."""

# Index: declarations module.Closed@L11, module.Subject@L17, Subject.geometry@L28, module.Prompt@L37, Prompt.meaningful@L49, module.Generation@L58, Generation.images@L74, module.Training@L87, Training.base@L104, module.Feedback@L113, module.DatasetImport@L124, module.ModelImport@L134; variables Id@L7, Text@L8, model_config@L14, name@L20, description@L21, tags@L22, framing@L23, negative@L24, region@L25, self@L28, bottom@L31, left@L31, right@L31, top@L31, description@L40, style@L41, tags@L42, negative_description@L43, negative_style@L44, negative_tags@L45, subjects@L46, self@L49, values@L51, s@L52, v@L53, model_id@L61, prompt@L62, seed@L63, width@L64, height@L65, steps@L66, guidance@L67, mode@L68, image_id@L69, mask_id@L70, strength@L71, self@L74, name@L90, dataset_ids@L91, steps@L92, resolution@L93, batch_size@L94, learning_rate@L95, seed@L96, device@L97, max_seconds@L98, resume_model_id@L99, mode@L100, base_model_id@L101, self@L104, score@L116, good@L117, change@L118, add@L119, remove@L120, allow_training@L121, name@L127, paths@L128, rights_confirmed@L131, name@L137, path@L138, kind@L139, license_note@L140. Purposes/parameters: docs/code-map.json.
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Id = Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")]
Text = Annotated[str, Field(max_length=2000)]


class Closed(BaseModel):
    """Reject unknown fields and non-finite floats at every user boundary."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Subject(Closed):
    """Named prompt section; optional normalized [left, top, right, bottom] spatial region."""

    name: Text = ""
    description: Text = ""
    tags: Text = ""
    framing: Text = ""
    negative: Text = ""
    region: tuple[float, float, float, float] | None = None

    @model_validator(mode="after")
    def geometry(self):
        """Reject flipped/out-of-bounds boxes instead of silently flattening placement."""
        if self.region is not None:
            left, top, right, bottom = self.region
            if not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
                raise ValueError("Subject region must have ordered normalized coordinates")
        return self


class Prompt(Closed):
    """Independent positive/negative scene, style, tags and subject input fields."""

    description: Text = ""
    style: Text = ""
    tags: Text = ""
    negative_description: Text = ""
    negative_style: Text = ""
    negative_tags: Text = ""
    subjects: list[Subject] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def meaningful(self):
        """At least one scene/style/tag/subject content field must be supplied."""
        values = [self.description, self.style, self.tags]
        values.extend(f"{s.description} {s.tags} {s.framing}" for s in self.subjects)
        if not any(v.strip() for v in values):
            raise ValueError("Enter at least one positive prompt field")
        return self


class Generation(Closed):
    """Model identity and bounded generation/edit settings; image IDs never arbitrary paths."""

    model_id: Id
    prompt: Prompt
    seed: int = Field(default=1337, ge=0, le=2**31 - 1)
    width: int = Field(default=256, ge=32, le=1024, multiple_of=8)
    height: int = Field(default=256, ge=32, le=1024, multiple_of=8)
    steps: int = Field(default=40, ge=1, le=100)
    guidance: float = Field(default=3.0, ge=1, le=12)
    mode: Literal["text", "edit", "inpaint", "expand"] = "text"
    image_id: Id | None = None
    mask_id: Id | None = None
    strength: float = Field(default=0.6, gt=0, le=1)

    @model_validator(mode="after")
    def images(self):
        """Require source/mask for relevant modes and forbid silent ignored input."""
        if self.mode != "text" and not self.image_id:
            raise ValueError("Editing needs an existing image")
        if self.mode == "inpaint" and not self.mask_id:
            raise ValueError("Inpainting needs a white-edit/black-preserve mask")
        if self.mode == "text" and (self.image_id or self.mask_id):
            raise ValueError("Text generation cannot take image inputs")
        if self.mode != "inpaint" and self.mask_id:
            raise ValueError("Masks apply only to inpainting")
        return self


class Training(Closed):
    """From-scratch or LoRA run: explicit datasets, compute limits and safe continuation."""

    name: Annotated[str, Field(min_length=1, max_length=80)]
    dataset_ids: list[Id] = Field(min_length=1, max_length=8)
    steps: int = Field(default=1000, ge=1, le=10000)
    resolution: Literal[32, 64, 128] = 32
    batch_size: int = Field(default=16, ge=1, le=32)
    learning_rate: float = Field(default=0.001, gt=0, le=0.01)
    seed: int = Field(default=1337, ge=0, le=2**31 - 1)
    device: Literal["auto", "cpu", "cuda"] = "auto"
    max_seconds: int = Field(default=1200, ge=10, le=7200)
    resume_model_id: Id | None = None
    mode: Literal["native", "lora"] = "native"
    base_model_id: Id | None = None

    @model_validator(mode="after")
    def base(self):
        """Distinguish a fresh native model from an adapter; do not mislabel either."""
        if (self.mode == "lora") != bool(self.base_model_id):
            raise ValueError("Only LoRA needs a base model")
        if self.mode == "lora" and self.resume_model_id:
            raise ValueError("LoRA optimizer resume is not implemented")
        return self


class Feedback(Closed):
    """Human score and structured revision notes; feedback never triggers hidden training."""

    score: int = Field(ge=-10, le=10)
    good: Text = ""
    change: Text = ""
    add: Text = ""
    remove: Text = ""
    allow_training: bool = False


class DatasetImport(Closed):
    """Operator-selected local directories/ZIP files with an explicit rights declaration."""

    name: Annotated[str, Field(min_length=1, max_length=80)]
    paths: list[Annotated[str, Field(min_length=1, max_length=1024)]] = Field(
        min_length=1, max_length=16
    )
    rights_confirmed: Literal[True]


class ModelImport(Closed):
    """Register a local native checkpoint or classic Stable Diffusion directory; no download."""

    name: Annotated[str, Field(min_length=1, max_length=80)]
    path: Annotated[str, Field(min_length=1, max_length=1024)]
    kind: Literal["native", "diffusers"]
    license_note: Annotated[str, Field(min_length=1, max_length=500)]
