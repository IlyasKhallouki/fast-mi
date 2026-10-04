;; Synthetic toy domain for the Fast Downward wrapper tests (Task 4.1).
;; Driving is one action but costs 10; walking costs 1 per leg. With the
;; metric in toy-problem.pddl the optimal plan is the three walks (cost 3),
;; which is longer than the one-action drive (cost 10).
(define (domain toy-travel)
  (:requirements :strips :typing :negative-preconditions :action-costs)
  (:types location)
  (:predicates (at ?l - location)
               (road ?from ?to - location)
               (path ?from ?to - location)
               (visited ?l - location))
  (:functions (total-cost) - number)
  (:action drive
    :parameters (?from ?to - location)
    :precondition (and (at ?from) (road ?from ?to) (not (visited ?to)))
    :effect (and (not (at ?from)) (at ?to) (visited ?to) (increase (total-cost) 10)))
  (:action walk
    :parameters (?from ?to - location)
    :precondition (and (at ?from) (path ?from ?to) (not (visited ?to)))
    :effect (and (not (at ?from)) (at ?to) (visited ?to) (increase (total-cost) 1))))
