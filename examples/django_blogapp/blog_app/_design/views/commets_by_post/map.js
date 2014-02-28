function(doc) {
  if (doc.doc_type == "Comment") {
    emit(doc.post, doc);
  }
}
