;; Synthetic toy problem: shortest plan (drive a d) costs 10, cheapest plan
;; (walk a b) (walk b c) (walk c d) costs 3.
(define (problem toy-travel-1)
  (:domain toy-travel)
  (:objects a b c d - location)
  (:init (at a) (visited a)
         (road a d)
         (path a b) (path b c) (path c d)
         (= (total-cost) 0))
  (:goal (at d))
  (:metric minimize (total-cost)))
