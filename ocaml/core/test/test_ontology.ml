(** Tests for Layer 1: Ontology Types *)

open Droit_core.Ontology

(** Test constructing actor values *)
let test_actor_construction () =
  let actor = make_actor
    ~id:"actor_001"
    ~name:"Acme Crypto Ltd"
    ~actor_type:CASP
    ~jurisdiction:"DE"
    ()
  in
  Alcotest.(check string) "actor id" "actor_001" actor.id;
  Alcotest.(check string) "actor name" "Acme Crypto Ltd" actor.name;
  Alcotest.(check (option string)) "jurisdiction" (Some "DE") actor.jurisdiction

(** Test constructing instrument values *)
let test_instrument_construction () =
  let instrument = make_instrument
    ~id:"inst_001"
    ~name:"StableCoin EUR"
    ~instrument_type:EMT
    ~issuer:"issuer_001"
    ()
  in
  Alcotest.(check string) "instrument id" "inst_001" instrument.id;
  Alcotest.(check string) "instrument name" "StableCoin EUR" instrument.name;
  Alcotest.(check (option string)) "issuer" (Some "issuer_001") instrument.issuer

(** Test constructing activity values *)
let test_activity_construction () =
  let activity = make_activity
    ~id:"act_001"
    ~name:"Custody Service"
    ~activity_type:Custody
    ~performed_by:"actor_001"
    ~involves_instrument:"inst_001"
    ()
  in
  Alcotest.(check string) "activity id" "act_001" activity.id;
  Alcotest.(check string) "activity name" "Custody Service" activity.name;
  Alcotest.(check (option string)) "performed_by" (Some "actor_001") activity.performed_by;
  Alcotest.(check (option string)) "involves_instrument" (Some "inst_001") activity.involves_instrument

(** Test constructing obligation values *)
let test_obligation_construction () =
  let obligation = make_obligation
    ~actor:CASP
    ~action:"Obtain authorization from competent authority"
    ~condition:(ActorIs CASP)
    ~deadline:"2024-12-30"
    ()
  in
  Alcotest.(check bool) "modality is Obligation"
    true (obligation.modality = Obligation);
  Alcotest.(check string) "action"
    "Obtain authorization from competent authority" obligation.action;
  Alcotest.(check (option string)) "deadline" (Some "2024-12-30") obligation.deadline

(** Test constructing permission values *)
let test_permission_construction () =
  let permission = make_permission
    ~actor:CreditInstitution
    ~action:"Provide crypto-asset services without CASP authorization"
    ~condition:(ActorIs CreditInstitution)
    ()
  in
  Alcotest.(check bool) "modality is Permission"
    true (permission.modality = Permission);
  Alcotest.(check string) "action"
    "Provide crypto-asset services without CASP authorization" permission.action

(** Test constructing prohibition values *)
let test_prohibition_construction () =
  let prohibition = make_prohibition
    ~actor:CASP
    ~action:"Provide services without authorization"
    ~condition:(Not (ActorIs CreditInstitution))
    ~penalty:"Administrative fine up to EUR 5,000,000"
    ()
  in
  Alcotest.(check bool) "modality is Prohibition"
    true (prohibition.modality = Prohibition);
  Alcotest.(check string) "action"
    "Provide services without authorization" prohibition.action;
  Alcotest.(check (option string)) "penalty"
    (Some "Administrative fine up to EUR 5,000,000") prohibition.penalty

(** Test constructing provision values *)
let test_provision_construction () =
  let obligation = make_obligation
    ~actor:CASP
    ~action:"Obtain authorization"
    ()
  in
  let permission = make_permission
    ~actor:CreditInstitution
    ~action:"Provide services under CRD authorization"
    ()
  in
  let provision = make_provision
    ~id:"mica_art36"
    ~title:"Authorization of crypto-asset service providers"
    ~source_document:"MiCA"
    ~source_article:"36"
    ~obligations:[obligation]
    ~permissions:[permission]
    ~temporal_scope:{ effective_from = Some "2024-12-30"; effective_to = None }
    ()
  in
  Alcotest.(check string) "provision id" "mica_art36" provision.id;
  Alcotest.(check string) "title"
    "Authorization of crypto-asset service providers" provision.title;
  Alcotest.(check string) "source_document" "MiCA" provision.source_document;
  Alcotest.(check string) "source_article" "36" provision.source_article;
  Alcotest.(check int) "obligations count" 1 (List.length provision.obligations);
  Alcotest.(check int) "permissions count" 1 (List.length provision.permissions);
  Alcotest.(check int) "prohibitions count" 0 (List.length provision.prohibitions)

(** Test YAML serialization round-trip for actor *)
let test_actor_yaml_roundtrip () =
  let actor = make_actor
    ~id:"actor_002"
    ~name:"Test Entity"
    ~actor_type:Issuer
    ()
  in
  let yaml = actor_to_yaml actor in
  match actor_of_yaml yaml with
  | Ok parsed ->
    Alcotest.(check string) "id roundtrip" actor.id parsed.id;
    Alcotest.(check string) "name roundtrip" actor.name parsed.name
  | Error msg ->
    Alcotest.fail ("YAML parsing failed: " ^ msg)

(** Test complex condition construction *)
let test_condition_construction () =
  let condition = And (
    ActorIs CASP,
    Or (
      ActivityIs Custody,
      ActivityIs Exchange
    )
  ) in
  (* Just verify it compiles and can be pattern matched *)
  match condition with
  | And (ActorIs CASP, Or (ActivityIs Custody, ActivityIs Exchange)) ->
    Alcotest.(check pass) "condition structure" () ()
  | _ ->
    Alcotest.fail "Unexpected condition structure"

(** Test RWA instrument construction *)
let test_rwa_instrument_construction () =
  let instrument = make_instrument
    ~id:"rwa_token_001"
    ~name:"Tokenized Property Fund"
    ~instrument_type:RWAProperty
    ~issuer:"originator_001"
    ()
  in
  Alcotest.(check string) "instrument id" "rwa_token_001" instrument.id;
  Alcotest.(check string) "instrument name" "Tokenized Property Fund" instrument.name;
  Alcotest.(check (option string)) "issuer" (Some "originator_001") instrument.issuer;
  (* Verify the type is RWAProperty *)
  Alcotest.(check bool) "is RWAProperty"
    true (instrument.instrument_type = RWAProperty)

(** Test RWA activity construction *)
let test_rwa_activity_construction () =
  let activity = make_activity
    ~id:"tokenization_001"
    ~name:"Property Tokenization"
    ~activity_type:Tokenization
    ~performed_by:"originator_001"
    ~involves_instrument:"rwa_token_001"
    ()
  in
  Alcotest.(check string) "activity id" "tokenization_001" activity.id;
  Alcotest.(check string) "activity name" "Property Tokenization" activity.name;
  Alcotest.(check bool) "is Tokenization"
    true (activity.activity_type = Tokenization)

(** Test RWA actor construction *)
let test_rwa_actor_construction () =
  let actor = make_actor
    ~id:"originator_001"
    ~name:"Prime Real Estate Holdings"
    ~actor_type:AssetOriginator
    ~jurisdiction:"EU"
    ()
  in
  Alcotest.(check string) "actor id" "originator_001" actor.id;
  Alcotest.(check string) "actor name" "Prime Real Estate Holdings" actor.name;
  Alcotest.(check bool) "is AssetOriginator"
    true (actor.actor_type = AssetOriginator)

(** Test RWA-specific obligation construction *)
let test_rwa_obligation_construction () =
  let obligation = make_obligation
    ~actor:AssetOriginator
    ~action:"Provide quarterly asset valuation reports"
    ~condition:(InstrumentIs RWAProperty)
    ()
  in
  Alcotest.(check bool) "modality is Obligation"
    true (obligation.modality = Obligation);
  Alcotest.(check string) "action"
    "Provide quarterly asset valuation reports" obligation.action

(** All ontology tests *)
let () =
  Alcotest.run "Ontology" [
    "actor", [
      Alcotest.test_case "construction" `Quick test_actor_construction;
      Alcotest.test_case "yaml roundtrip" `Quick test_actor_yaml_roundtrip;
    ];
    "instrument", [
      Alcotest.test_case "construction" `Quick test_instrument_construction;
    ];
    "activity", [
      Alcotest.test_case "construction" `Quick test_activity_construction;
    ];
    "obligation", [
      Alcotest.test_case "construction" `Quick test_obligation_construction;
    ];
    "permission", [
      Alcotest.test_case "construction" `Quick test_permission_construction;
    ];
    "prohibition", [
      Alcotest.test_case "construction" `Quick test_prohibition_construction;
    ];
    "provision", [
      Alcotest.test_case "construction" `Quick test_provision_construction;
    ];
    "condition", [
      Alcotest.test_case "construction" `Quick test_condition_construction;
    ];
    "rwa", [
      Alcotest.test_case "instrument construction" `Quick test_rwa_instrument_construction;
      Alcotest.test_case "activity construction" `Quick test_rwa_activity_construction;
      Alcotest.test_case "actor construction" `Quick test_rwa_actor_construction;
      Alcotest.test_case "obligation construction" `Quick test_rwa_obligation_construction;
    ];
  ]
