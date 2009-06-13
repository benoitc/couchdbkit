function(doc) { 
     if (doc.doc_type == "Greeting") 
          emit(doc._id, doc); 
}