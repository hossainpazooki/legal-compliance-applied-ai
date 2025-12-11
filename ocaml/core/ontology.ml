(** Layer 1: Legal Ontology Types

    This module defines the core legal concepts used throughout the
    regulatory compliance system. These types model provisions, deontic
    modalities (obligation/permission/prohibition), actors, instruments,
    activities, and conditions.
*)

(** Unique identifier for provisions *)
type provision_id = string

(** Unique identifier for actors *)
type actor_id = string

(** Unique identifier for instruments *)
type instrument_id = string

(** Unique identifier for activities *)
type activity_id = string

(** Actor classification in the regulatory domain *)
type actor_type =
  | NaturalPerson
  | LegalEntity
  | CreditInstitution
  | InvestmentFirm
  | CASP  (** Crypto-Asset Service Provider *)
  | Issuer
  | Regulator
  | AssetOriginator  (** RWA: Entity that owns/originates the real-world asset *)
  | Custodian        (** Custodian of assets (crypto or traditional) *)
  | OtherActor of string

let actor_type_to_string = function
  | NaturalPerson -> "NaturalPerson"
  | LegalEntity -> "LegalEntity"
  | CreditInstitution -> "CreditInstitution"
  | InvestmentFirm -> "InvestmentFirm"
  | CASP -> "CASP"
  | Issuer -> "Issuer"
  | Regulator -> "Regulator"
  | AssetOriginator -> "AssetOriginator"
  | Custodian -> "Custodian"
  | OtherActor s -> s

let actor_type_of_string = function
  | "NaturalPerson" -> NaturalPerson
  | "LegalEntity" -> LegalEntity
  | "CreditInstitution" -> CreditInstitution
  | "InvestmentFirm" -> InvestmentFirm
  | "CASP" -> CASP
  | "Issuer" -> Issuer
  | "Regulator" -> Regulator
  | "AssetOriginator" -> AssetOriginator
  | "Custodian" -> Custodian
  | s -> OtherActor s

let actor_type_to_yaml t = `String (actor_type_to_string t)

let actor_type_of_yaml = function
  | `String s -> Ok (actor_type_of_string s)
  | _ -> Error "Expected string for actor_type"

(** An actor subject to or benefiting from regulatory provisions *)
type actor = {
  id : actor_id;
  name : string;
  actor_type : actor_type;
  jurisdiction : string option;
}

let actor_to_yaml a =
  `O ([
    ("id", `String a.id);
    ("name", `String a.name);
    ("actor_type", actor_type_to_yaml a.actor_type);
  ] @ match a.jurisdiction with
    | Some j -> [("jurisdiction", `String j)]
    | None -> [])

let actor_of_yaml = function
  | `O fields ->
    let get k = List.assoc_opt k fields in
    (match get "id", get "name", get "actor_type" with
    | Some (`String id), Some (`String name), Some at ->
      (match actor_type_of_yaml at with
      | Ok actor_type ->
        let jurisdiction = match get "jurisdiction" with
          | Some (`String j) -> Some j
          | _ -> None
        in
        Ok { id; name; actor_type; jurisdiction }
      | Error e -> Error e)
    | _ -> Error "Missing required fields for actor")
  | _ -> Error "Expected object for actor"

(** Classification of crypto-assets and tokenized instruments *)
type instrument_type =
  | ART   (** Asset-Referenced Token (MiCA) *)
  | EMT   (** E-Money Token (MiCA) *)
  | UtilityToken
  | SecurityToken
  | RWAToken  (** Real-World Asset Token *)
  | RWADebt   (** Tokenized Debt Instrument *)
  | RWAEquity (** Tokenized Equity *)
  | RWAProperty (** Tokenized Real Estate / Property *)
  | OtherInstrument of string

let instrument_type_to_string = function
  | ART -> "ART"
  | EMT -> "EMT"
  | UtilityToken -> "UtilityToken"
  | SecurityToken -> "SecurityToken"
  | RWAToken -> "RWAToken"
  | RWADebt -> "RWADebt"
  | RWAEquity -> "RWAEquity"
  | RWAProperty -> "RWAProperty"
  | OtherInstrument s -> s

let instrument_type_of_string = function
  | "ART" -> ART
  | "EMT" -> EMT
  | "UtilityToken" -> UtilityToken
  | "SecurityToken" -> SecurityToken
  | "RWAToken" -> RWAToken
  | "RWADebt" -> RWADebt
  | "RWAEquity" -> RWAEquity
  | "RWAProperty" -> RWAProperty
  | s -> OtherInstrument s

let instrument_type_to_yaml t = `String (instrument_type_to_string t)

let instrument_type_of_yaml = function
  | `String s -> Ok (instrument_type_of_string s)
  | _ -> Error "Expected string for instrument_type"

(** A financial instrument or crypto-asset *)
type instrument = {
  id : instrument_id;
  name : string;
  instrument_type : instrument_type;
  issuer : actor_id option;
}

let instrument_to_yaml i =
  `O ([
    ("id", `String i.id);
    ("name", `String i.name);
    ("instrument_type", instrument_type_to_yaml i.instrument_type);
  ] @ match i.issuer with
    | Some iss -> [("issuer", `String iss)]
    | None -> [])

let instrument_of_yaml = function
  | `O fields ->
    let get k = List.assoc_opt k fields in
    (match get "id", get "name", get "instrument_type" with
    | Some (`String id), Some (`String name), Some it ->
      (match instrument_type_of_yaml it with
      | Ok instrument_type ->
        let issuer = match get "issuer" with
          | Some (`String i) -> Some i
          | _ -> None
        in
        Ok { id; name; instrument_type; issuer }
      | Error e -> Error e)
    | _ -> Error "Missing required fields for instrument")
  | _ -> Error "Expected object for instrument"

(** Regulated activities *)
type activity_type =
  | Issuance
  | PublicOffer
  | AdmissionToTrading
  | Custody
  | Exchange
  | Transfer
  | Advice
  | PortfolioManagement
  | Tokenization  (** RWA: Converting real-world asset to on-chain token *)
  | Disclosure    (** RWA: Ongoing disclosure of asset information *)
  | Valuation     (** RWA: Asset valuation and pricing *)
  | OtherActivity of string

let activity_type_to_string = function
  | Issuance -> "Issuance"
  | PublicOffer -> "PublicOffer"
  | AdmissionToTrading -> "AdmissionToTrading"
  | Custody -> "Custody"
  | Exchange -> "Exchange"
  | Transfer -> "Transfer"
  | Advice -> "Advice"
  | PortfolioManagement -> "PortfolioManagement"
  | Tokenization -> "Tokenization"
  | Disclosure -> "Disclosure"
  | Valuation -> "Valuation"
  | OtherActivity s -> s

let activity_type_of_string = function
  | "Issuance" -> Issuance
  | "PublicOffer" -> PublicOffer
  | "AdmissionToTrading" -> AdmissionToTrading
  | "Custody" -> Custody
  | "Exchange" -> Exchange
  | "Transfer" -> Transfer
  | "Advice" -> Advice
  | "PortfolioManagement" -> PortfolioManagement
  | "Tokenization" -> Tokenization
  | "Disclosure" -> Disclosure
  | "Valuation" -> Valuation
  | s -> OtherActivity s

let activity_type_to_yaml t = `String (activity_type_to_string t)

let activity_type_of_yaml = function
  | `String s -> Ok (activity_type_of_string s)
  | _ -> Error "Expected string for activity_type"

(** An activity that may be subject to regulation *)
type activity = {
  id : activity_id;
  name : string;
  activity_type : activity_type;
  performed_by : actor_id option;
  involves_instrument : instrument_id option;
}

let activity_to_yaml a =
  `O ([
    ("id", `String a.id);
    ("name", `String a.name);
    ("activity_type", activity_type_to_yaml a.activity_type);
  ] @ (match a.performed_by with
    | Some p -> [("performed_by", `String p)]
    | None -> [])
  @ (match a.involves_instrument with
    | Some i -> [("involves_instrument", `String i)]
    | None -> []))

let activity_of_yaml = function
  | `O fields ->
    let get k = List.assoc_opt k fields in
    (match get "id", get "name", get "activity_type" with
    | Some (`String id), Some (`String name), Some at ->
      (match activity_type_of_yaml at with
      | Ok activity_type ->
        let performed_by = match get "performed_by" with
          | Some (`String p) -> Some p
          | _ -> None
        in
        let involves_instrument = match get "involves_instrument" with
          | Some (`String i) -> Some i
          | _ -> None
        in
        Ok { id; name; activity_type; performed_by; involves_instrument }
      | Error e -> Error e)
    | _ -> Error "Missing required fields for activity")
  | _ -> Error "Expected object for activity"

(** Temporal bounds for provisions *)
type temporal_scope = {
  effective_from : string option;  (** ISO 8601 date *)
  effective_to : string option;    (** ISO 8601 date *)
}

let temporal_scope_to_yaml t =
  `O ([
  ] @ (match t.effective_from with
    | Some d -> [("effective_from", `String d)]
    | None -> [])
  @ (match t.effective_to with
    | Some d -> [("effective_to", `String d)]
    | None -> []))

let temporal_scope_of_yaml = function
  | `O fields ->
    let get k = List.assoc_opt k fields in
    let effective_from = match get "effective_from" with
      | Some (`String d) -> Some d
      | _ -> None
    in
    let effective_to = match get "effective_to" with
      | Some (`String d) -> Some d
      | _ -> None
    in
    Ok { effective_from; effective_to }
  | _ -> Error "Expected object for temporal_scope"

(** A condition that must hold for a provision to apply *)
type condition =
  | ActorIs of actor_type
  | InstrumentIs of instrument_type
  | ActivityIs of activity_type
  | JurisdictionIs of string
  | ThresholdExceeds of { field : string; value : float }
  | ThresholdBelow of { field : string; value : float }
  | And of condition * condition
  | Or of condition * condition
  | Not of condition
  | True
  | False

let rec condition_to_yaml = function
  | ActorIs at -> `O [("ActorIs", actor_type_to_yaml at)]
  | InstrumentIs it -> `O [("InstrumentIs", instrument_type_to_yaml it)]
  | ActivityIs at -> `O [("ActivityIs", activity_type_to_yaml at)]
  | JurisdictionIs j -> `O [("JurisdictionIs", `String j)]
  | ThresholdExceeds { field; value } ->
    `O [("ThresholdExceeds", `O [("field", `String field); ("value", `Float value)])]
  | ThresholdBelow { field; value } ->
    `O [("ThresholdBelow", `O [("field", `String field); ("value", `Float value)])]
  | And (c1, c2) -> `O [("And", `A [condition_to_yaml c1; condition_to_yaml c2])]
  | Or (c1, c2) -> `O [("Or", `A [condition_to_yaml c1; condition_to_yaml c2])]
  | Not c -> `O [("Not", condition_to_yaml c)]
  | True -> `String "True"
  | False -> `String "False"

let rec condition_of_yaml = function
  | `String "True" -> Ok True
  | `String "False" -> Ok False
  | `O [("ActorIs", v)] ->
    (match actor_type_of_yaml v with
    | Ok at -> Ok (ActorIs at)
    | Error e -> Error e)
  | `O [("InstrumentIs", v)] ->
    (match instrument_type_of_yaml v with
    | Ok it -> Ok (InstrumentIs it)
    | Error e -> Error e)
  | `O [("ActivityIs", v)] ->
    (match activity_type_of_yaml v with
    | Ok at -> Ok (ActivityIs at)
    | Error e -> Error e)
  | `O [("JurisdictionIs", `String j)] -> Ok (JurisdictionIs j)
  | `O [("ThresholdExceeds", `O fields)] ->
    (match List.assoc_opt "field" fields, List.assoc_opt "value" fields with
    | Some (`String field), Some (`Float value) ->
      Ok (ThresholdExceeds { field; value })
    | _ -> Error "Invalid ThresholdExceeds")
  | `O [("ThresholdBelow", `O fields)] ->
    (match List.assoc_opt "field" fields, List.assoc_opt "value" fields with
    | Some (`String field), Some (`Float value) ->
      Ok (ThresholdBelow { field; value })
    | _ -> Error "Invalid ThresholdBelow")
  | `O [("And", `A [c1; c2])] ->
    (match condition_of_yaml c1, condition_of_yaml c2 with
    | Ok c1, Ok c2 -> Ok (And (c1, c2))
    | Error e, _ | _, Error e -> Error e)
  | `O [("Or", `A [c1; c2])] ->
    (match condition_of_yaml c1, condition_of_yaml c2 with
    | Ok c1, Ok c2 -> Ok (Or (c1, c2))
    | Error e, _ | _, Error e -> Error e)
  | `O [("Not", c)] ->
    (match condition_of_yaml c with
    | Ok c -> Ok (Not c)
    | Error e -> Error e)
  | _ -> Error "Invalid condition"

(** Deontic modality: what the provision requires/permits/prohibits *)
type deontic_modality =
  | Obligation   (** Must do *)
  | Permission   (** May do *)
  | Prohibition  (** Must not do *)

let deontic_modality_to_string = function
  | Obligation -> "Obligation"
  | Permission -> "Permission"
  | Prohibition -> "Prohibition"

let deontic_modality_of_string = function
  | "Obligation" -> Ok Obligation
  | "Permission" -> Ok Permission
  | "Prohibition" -> Ok Prohibition
  | s -> Error ("Unknown modality: " ^ s)

let deontic_modality_to_yaml m = `String (deontic_modality_to_string m)

let deontic_modality_of_yaml = function
  | `String s -> deontic_modality_of_string s
  | _ -> Error "Expected string for deontic_modality"

(** An obligation imposed by a provision *)
type obligation = {
  modality : deontic_modality;  (** Always Obligation *)
  actor : actor_type;
  action : string;
  condition : condition option;
  deadline : string option;
}

let obligation_to_yaml o =
  `O ([
    ("modality", deontic_modality_to_yaml o.modality);
    ("actor", actor_type_to_yaml o.actor);
    ("action", `String o.action);
  ] @ (match o.condition with
    | Some c -> [("condition", condition_to_yaml c)]
    | None -> [])
  @ (match o.deadline with
    | Some d -> [("deadline", `String d)]
    | None -> []))

let obligation_of_yaml = function
  | `O fields ->
    let get k = List.assoc_opt k fields in
    (match get "modality", get "actor", get "action" with
    | Some m, Some a, Some (`String action) ->
      (match deontic_modality_of_yaml m, actor_type_of_yaml a with
      | Ok modality, Ok actor ->
        let condition = match get "condition" with
          | Some c -> (match condition_of_yaml c with Ok c -> Some c | _ -> None)
          | None -> None
        in
        let deadline = match get "deadline" with
          | Some (`String d) -> Some d
          | _ -> None
        in
        Ok { modality; actor; action; condition; deadline }
      | Error e, _ | _, Error e -> Error e)
    | _ -> Error "Missing required fields for obligation")
  | _ -> Error "Expected object for obligation"

(** A permission granted by a provision *)
type permission = {
  modality : deontic_modality;  (** Always Permission *)
  actor : actor_type;
  action : string;
  condition : condition option;
}

let permission_to_yaml p =
  `O ([
    ("modality", deontic_modality_to_yaml p.modality);
    ("actor", actor_type_to_yaml p.actor);
    ("action", `String p.action);
  ] @ (match p.condition with
    | Some c -> [("condition", condition_to_yaml c)]
    | None -> []))

let permission_of_yaml = function
  | `O fields ->
    let get k = List.assoc_opt k fields in
    (match get "modality", get "actor", get "action" with
    | Some m, Some a, Some (`String action) ->
      (match deontic_modality_of_yaml m, actor_type_of_yaml a with
      | Ok modality, Ok actor ->
        let condition = match get "condition" with
          | Some c -> (match condition_of_yaml c with Ok c -> Some c | _ -> None)
          | None -> None
        in
        Ok { modality; actor; action; condition }
      | Error e, _ | _, Error e -> Error e)
    | _ -> Error "Missing required fields for permission")
  | _ -> Error "Expected object for permission"

(** A prohibition imposed by a provision *)
type prohibition = {
  modality : deontic_modality;  (** Always Prohibition *)
  actor : actor_type;
  action : string;
  condition : condition option;
  penalty : string option;
}

let prohibition_to_yaml p =
  `O ([
    ("modality", deontic_modality_to_yaml p.modality);
    ("actor", actor_type_to_yaml p.actor);
    ("action", `String p.action);
  ] @ (match p.condition with
    | Some c -> [("condition", condition_to_yaml c)]
    | None -> [])
  @ (match p.penalty with
    | Some pen -> [("penalty", `String pen)]
    | None -> []))

let prohibition_of_yaml = function
  | `O fields ->
    let get k = List.assoc_opt k fields in
    (match get "modality", get "actor", get "action" with
    | Some m, Some a, Some (`String action) ->
      (match deontic_modality_of_yaml m, actor_type_of_yaml a with
      | Ok modality, Ok actor ->
        let condition = match get "condition" with
          | Some c -> (match condition_of_yaml c with Ok c -> Some c | _ -> None)
          | None -> None
        in
        let penalty = match get "penalty" with
          | Some (`String p) -> Some p
          | _ -> None
        in
        Ok { modality; actor; action; condition; penalty }
      | Error e, _ | _, Error e -> Error e)
    | _ -> Error "Missing required fields for prohibition")
  | _ -> Error "Expected object for prohibition"

(** A legal provision that may contain obligations, permissions, or prohibitions *)
type provision = {
  id : provision_id;
  title : string;
  source_document : string;
  source_article : string;
  obligations : obligation list;
  permissions : permission list;
  prohibitions : prohibition list;
  temporal_scope : temporal_scope option;
  supersedes : provision_id list;
}

let provision_to_yaml p =
  let obligations_yaml = `A (List.map obligation_to_yaml p.obligations) in
  let permissions_yaml = `A (List.map permission_to_yaml p.permissions) in
  let prohibitions_yaml = `A (List.map prohibition_to_yaml p.prohibitions) in
  let supersedes_yaml = `A (List.map (fun s -> `String s) p.supersedes) in
  `O ([
    ("id", `String p.id);
    ("title", `String p.title);
    ("source_document", `String p.source_document);
    ("source_article", `String p.source_article);
    ("obligations", obligations_yaml);
    ("permissions", permissions_yaml);
    ("prohibitions", prohibitions_yaml);
    ("supersedes", supersedes_yaml);
  ] @ (match p.temporal_scope with
    | Some t -> [("temporal_scope", temporal_scope_to_yaml t)]
    | None -> []))

let provision_of_yaml = function
  | `O fields ->
    let get k = List.assoc_opt k fields in
    (match get "id", get "title", get "source_document", get "source_article" with
    | Some (`String id), Some (`String title),
      Some (`String source_document), Some (`String source_article) ->
      let parse_list parser = function
        | Some (`A items) ->
          List.filter_map (fun item ->
            match parser item with Ok x -> Some x | Error _ -> None
          ) items
        | _ -> []
      in
      let obligations = parse_list obligation_of_yaml (get "obligations") in
      let permissions = parse_list permission_of_yaml (get "permissions") in
      let prohibitions = parse_list prohibition_of_yaml (get "prohibitions") in
      let supersedes = match get "supersedes" with
        | Some (`A items) ->
          List.filter_map (function `String s -> Some s | _ -> None) items
        | _ -> []
      in
      let temporal_scope = match get "temporal_scope" with
        | Some t -> (match temporal_scope_of_yaml t with Ok ts -> Some ts | _ -> None)
        | None -> None
      in
      Ok { id; title; source_document; source_article;
           obligations; permissions; prohibitions;
           temporal_scope; supersedes }
    | _ -> Error "Missing required fields for provision")
  | _ -> Error "Expected object for provision"

(** Helper constructors *)

let make_actor ~id ~name ~actor_type ?jurisdiction () =
  { id; name; actor_type; jurisdiction }

let make_instrument ~id ~name ~instrument_type ?issuer () =
  { id; name; instrument_type; issuer }

let make_activity ~id ~name ~activity_type ?performed_by ?involves_instrument () =
  { id; name; activity_type; performed_by; involves_instrument }

let make_obligation ~actor ~action ?condition ?deadline () =
  { modality = Obligation; actor; action; condition; deadline }

let make_permission ~actor ~action ?condition () =
  { modality = Permission; actor; action; condition }

let make_prohibition ~actor ~action ?condition ?penalty () =
  { modality = Prohibition; actor; action; condition; penalty }

let make_provision ~id ~title ~source_document ~source_article
    ?(obligations=[]) ?(permissions=[]) ?(prohibitions=[])
    ?temporal_scope ?(supersedes=[]) () =
  { id; title; source_document; source_article;
    obligations; permissions; prohibitions;
    temporal_scope; supersedes }
